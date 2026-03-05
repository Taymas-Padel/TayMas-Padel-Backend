from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, localtime
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime, time, timedelta
from django.db import transaction
from django.db.models import Q
from decimal import Decimal

from .models import Booking
from memberships.models import UserMembership
from inventory.models import Service
from courts.models import Court
from .serializers import (
    BookingSerializer,
    CreateBookingSerializer,
    SlotAvailabilitySerializer,
    ManagerScheduleSerializer,
)
from finance.models import Transaction
from courts.models import Court
from core.models import ClubSetting, ClosedDay
from users.permissions import IsReceptionist, IsAdminRole
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()


# ---------------------------------------------------------------------------
# 1. ОТМЕНА БРОНИ
# ---------------------------------------------------------------------------

class CancelBookingView(APIView):
    """POST /api/bookings/<id>/cancel/ — отмена брони (клиент или ресепшн)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        user = request.user
        now = timezone.now()

        is_staff = user.role in ['ADMIN', 'RECEPTIONIST']
        is_coach_of_booking = booking.coach_id == user.id

        if booking.user != user and not is_staff and not is_coach_of_booking:
            return Response({"detail": "Вы не можете отменить чужую бронь."}, status=403)

        if booking.status == 'CANCELED':
            return Response({"detail": "Бронирование уже отменено."}, status=400)

        if booking.start_time <= now:
            return Response({"detail": "Нельзя отменить прошедшее бронирование."}, status=400)

        setting = ClubSetting.objects.filter(key='CANCELLATION_HOURS').first()
        limit_hours = int(setting.value) if setting else 24
        hours_left = (booking.start_time - now).total_seconds() / 3600

        if hours_left < limit_hours and not is_staff and not is_coach_of_booking:
            return Response(
                {"detail": f"Отмена доступна только за {limit_hours} ч до начала."},
                status=400,
            )

        booking.status = 'CANCELED'
        booking.save(update_fields=['status'])

        # Возврат часов на абонемент, если бронь была оплачена часами
        if booking.membership_used:
            from decimal import Decimal
            membership = booking.membership_used
            hours_return = Decimal(str(booking.duration_hours))
            membership.hours_remaining += hours_return
            if membership.hours_remaining > 0:
                membership.is_active = True
            membership.save(update_fields=['hours_remaining', 'is_active'])

        if booking.price > 0 and booking.is_paid:
            Transaction.objects.create(
                user=booking.user,
                booking=booking,
                amount=-booking.price,
                transaction_type=Transaction.TransactionType.REFUND,
                payment_method=Transaction.PaymentMethod.UNKNOWN,
                description=f"Возврат по отменённой брони #{booking.id}",
            )

        return Response({"status": "Бронирование отменено."})


# ---------------------------------------------------------------------------
# 2. СПИСОК БРОНЕЙ КЛИЕНТА (предстоящие / история)
# ---------------------------------------------------------------------------

class UserBookingsListView(generics.ListAPIView):
    """GET /api/bookings/ — предстоящие брони текущего пользователя."""
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'RECEPTIONIST']:
            return Booking.objects.all().order_by('-start_time')
        return Booking.objects.filter(
            Q(user=user) | Q(participants=user)
        ).exclude(status='CANCELED').filter(
            end_time__gte=timezone.now()
        ).distinct().order_by('start_time')


class UserBookingHistoryView(generics.ListAPIView):
    """GET /api/bookings/history/ — история броней (включая отменённые и прошедшие)."""
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Booking.objects.filter(
            Q(user=user) | Q(participants=user)
        ).distinct().order_by('-start_time')


class CoachScheduleView(generics.ListAPIView):
    """
    GET /api/bookings/coach/schedule/?from=YYYY-MM-DD&to=YYYY-MM-DD
    Расписание броней тренера (брони, где он назначен). Без параметров — с сегодня по +14 дней.
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role not in ['COACH_PADEL', 'COACH_FITNESS', 'ADMIN']:
            return Booking.objects.none()
        qs = Booking.objects.filter(coach=user).select_related('court', 'user').order_by('start_time')
        from_date = self.request.query_params.get('from')
        to_date = self.request.query_params.get('to')
        now = timezone.now()
        today = now.date()
        if from_date:
            try:
                start = datetime.strptime(from_date, '%Y-%m-%d').date()
            except ValueError:
                start = today
        else:
            start = today
        if to_date:
            try:
                end = datetime.strptime(to_date, '%Y-%m-%d').date()
            except ValueError:
                end = start + timedelta(days=14)
        else:
            end = start + timedelta(days=14)
        return qs.filter(
            start_time__date__gte=start,
            start_time__date__lte=end,
        )


class BookingDetailView(generics.RetrieveAPIView):
    """GET /api/bookings/<id>/ — детали конкретной брони."""
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'RECEPTIONIST']:
            return Booking.objects.all()
        return Booking.objects.filter(
            Q(user=user) | Q(participants=user) | Q(coach=user)
        ).distinct()


# ---------------------------------------------------------------------------
# 3. СОЗДАНИЕ БРОНИ (клиент создаёт для себя)
# ---------------------------------------------------------------------------

class CreateBookingView(generics.CreateAPIView):
    """POST /api/bookings/create/ — создать бронь."""
    queryset = Booking.objects.all()
    serializer_class = CreateBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        court_id = request.data.get('court')
        if not court_id:
            return Response({"court": ["Обязательное поле"]}, status=400)

        try:
            with transaction.atomic():
                try:
                    Court.objects.select_for_update().get(id=court_id)
                except Court.DoesNotExist:
                    return Response({"detail": "Корт не найден"}, status=404)

                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# 4. СОЗДАНИЕ БРОНИ РЕСЕПШН (от имени клиента)
# ---------------------------------------------------------------------------

class ReceptionCreateBookingView(generics.CreateAPIView):
    """
    POST /api/bookings/reception/create/
    Ресепшн/Админ создаёт бронь от имени клиента.
    Тело запроса: всё то же, что и обычная бронь + поле client_id (ID клиента).
    """
    queryset = Booking.objects.all()
    serializer_class = CreateBookingSerializer
    permission_classes = [IsReceptionist]

    def create(self, request, *args, **kwargs):
        client_id = request.data.get('client_id')
        if not client_id:
            return Response({"client_id": ["Укажите ID клиента."]}, status=400)

        client = get_object_or_404(User, pk=client_id)
        court_id = request.data.get('court')
        if not court_id:
            return Response({"court": ["Обязательное поле"]}, status=400)

        try:
            with transaction.atomic():
                Court.objects.select_for_update().get(id=court_id)
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(user=client)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Court.DoesNotExist:
            return Response({"detail": "Корт не найден"}, status=404)
        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


# ---------------------------------------------------------------------------
# 5. ПОДТВЕРЖДЕНИЕ ОПЛАТЫ РЕСЕПШН
# ---------------------------------------------------------------------------

class ClientConfirmBookingView(APIView):
    """
    POST /api/bookings/<id>/client-confirm/
    Клиент «подтверждает» бронь (PENDING → CONFIRMED), но без списания.
    Используется, когда оплата будет произведена на стойке или членство покрывает.
    Если membership_used=True и часы списаны — бронь сразу CONFIRMED.
    Иначе устанавливает статус CONFIRMED, is_paid остаётся False.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        user = request.user

        if booking.user != user and user.role not in ['ADMIN', 'RECEPTIONIST']:
            return Response({"detail": "Нет доступа."}, status=403)
        if booking.status == 'CANCELED':
            return Response({"detail": "Нельзя подтвердить отменённую бронь."}, status=400)
        if booking.status == 'CONFIRMED':
            return Response({"detail": "Бронь уже подтверждена."})

        booking.status = 'CONFIRMED'
        booking.save(update_fields=['status'])
        return Response({"status": "Бронь подтверждена.", "booking_id": booking.id})


class ConfirmPaymentView(APIView):
    """
    POST /api/bookings/<id>/confirm-payment/
    Ресепшн фиксирует получение оплаты (PENDING → CONFIRMED + is_paid=True).
    Тело: { "payment_method": "CASH" | "KASPI" | "CARD" }
    """
    permission_classes = [IsReceptionist]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)

        if booking.status == 'CANCELED':
            return Response({"detail": "Нельзя подтвердить отменённую бронь."}, status=400)

        if booking.is_paid:
            return Response({"detail": "Бронь уже оплачена."}, status=400)

        method_raw = request.data.get('payment_method', 'UNKNOWN')
        valid_methods = [c[0] for c in Transaction.PaymentMethod.choices]
        if method_raw not in valid_methods:
            method_raw = 'UNKNOWN'

        with transaction.atomic():
            booking.is_paid = True
            booking.status = 'CONFIRMED'
            booking.save(update_fields=['is_paid', 'status'])

            Transaction.objects.create(
                user=booking.user,
                booking=booking,
                amount=booking.price,
                amount_court=booking.price,
                transaction_type=Transaction.TransactionType.BOOKING_PAYMENT,
                payment_method=method_raw,
                description=f"Оплата на ресепшн за бронь #{booking.id}",
            )

        return Response({
            "status": "Оплата подтверждена.",
            "booking_id": booking.id,
            "is_paid": booking.is_paid,
            "payment_method": method_raw,
        })


# ---------------------------------------------------------------------------
# 6. ПРОВЕРКА СВОБОДНЫХ СЛОТОВ
# ---------------------------------------------------------------------------

class CheckAvailabilityView(APIView):
    """GET /api/bookings/check-availability/?court_id=1&date=2025-12-20"""
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('court_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', required=True),
        ]
    )
    def get(self, request):
        serializer = SlotAvailabilitySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        court_id = serializer.validated_data['court_id']
        date_obj = serializer.validated_data['date']

        closed_day = ClosedDay.objects.filter(date=date_obj).first()
        if closed_day:
            return Response({
                "court_id": court_id, "date": date_obj,
                "is_holiday": True,
                "reason": closed_day.reason or "Санитарный день",
                "busy_slots": [],
            })

        open_s = ClubSetting.objects.filter(key='OPEN_TIME').first()
        close_s = ClubSetting.objects.filter(key='CLOSE_TIME').first()
        open_h = int(open_s.value.split(':')[0]) if open_s else 7
        close_h = int(close_s.value.split(':')[0]) if close_s else 23

        day_start = make_aware(datetime.combine(date_obj, time(open_h, 0)))
        day_end = make_aware(datetime.combine(date_obj, time(close_h, 0)))

        bookings = Booking.objects.filter(
            court_id=court_id,
            end_time__gt=day_start,
            start_time__lt=day_end,
        ).exclude(status='CANCELED')

        busy_slots = []
        for b in bookings:
            local_start = localtime(b.start_time)
            local_end = localtime(b.end_time)
            busy_slots.append({
                "start": local_start.strftime('%H:%M'),
                "end": local_end.strftime('%H:%M'),
                "booking_id": b.id,
            })

        return Response({
            "court_id": court_id,
            "date": date_obj,
            "work_hours": f"{open_h}:00 – {close_h}:00",
            "is_holiday": False,
            "busy_slots": sorted(busy_slots, key=lambda x: x['start']),
        })


# ---------------------------------------------------------------------------
# 7. РАСПИСАНИЕ ДЛЯ РЕСЕПШН/МЕНЕДЖЕРА
# ---------------------------------------------------------------------------

class ManagerScheduleView(APIView):
    """GET /api/bookings/manager/schedule/?date=YYYY-MM-DD — расписание по кортам."""
    permission_classes = [IsReceptionist]  # ИСПРАВЛЕНО: было IsAdminUser

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description="Дата YYYY-MM-DD (по умолчанию сегодня)")
        ]
    )
    def get(self, request):
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Неверный формат даты. Используйте YYYY-MM-DD"}, status=400)
        else:
            target_date = timezone.now().date()

        day_start = make_aware(datetime.combine(target_date, time(0, 0)))
        day_end = make_aware(datetime.combine(target_date, time(23, 59, 59)))

        courts = Court.objects.all()
        response_data = []

        for court in courts:
            bookings = Booking.objects.filter(
                court=court,
                start_time__gte=day_start,
                start_time__lte=day_end,
            ).exclude(status='CANCELED').order_by('start_time')

            serializer = ManagerScheduleSerializer(bookings, many=True)
            response_data.append({
                "court_id": court.id,
                "court_name": court.name,
                "court_type": court.court_type,
                "bookings": serializer.data,
            })

        return Response({"date": target_date, "schedule": response_data})


# ---------------------------------------------------------------------------
# 8. СПИСОК ВСЕХ БРОНЕЙ ДЛЯ CRM (с фильтрами)
# ---------------------------------------------------------------------------

class AllBookingsView(generics.ListAPIView):
    """
    GET /api/bookings/all/?date=&status=&court_id=
    Полный список броней для ресепшн/админа.
    """
    serializer_class = ManagerScheduleSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        qs = Booking.objects.select_related('user', 'court', 'coach').all()

        date_str = self.request.query_params.get('date')
        if date_str:
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
                day_start = make_aware(datetime.combine(d, time(0, 0)))
                day_end = make_aware(datetime.combine(d, time(23, 59, 59)))
                qs = qs.filter(start_time__gte=day_start, start_time__lte=day_end)
            except ValueError:
                pass

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        court_id = self.request.query_params.get('court_id')
        if court_id:
            qs = qs.filter(court_id=court_id)

        client_id = self.request.query_params.get('client_id')
        if client_id:
            qs = qs.filter(user_id=client_id)

        return qs.order_by('-start_time')


# ---------------------------------------------------------------------------
# 9. СВОБОДНЫЕ ТРЕНЕРЫ НА ВЫБРАННОЕ ВРЕМЯ
# ---------------------------------------------------------------------------

class AvailableCoachesView(APIView):
    """
    GET /api/bookings/available-coaches/?datetime=2025-02-25T14:00:00&duration=60
    Возвращает тренеров, у которых нет брони в указанный слот.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        dt_str = request.query_params.get('datetime')
        duration = int(request.query_params.get('duration', 60))
        if not dt_str:
            return Response({"error": "Укажите datetime (ISO)."}, status=400)
        start_slot = parse_datetime(dt_str)
        if start_slot is None:
            return Response({"error": "Неверный формат datetime (ожидается ISO, напр. 2026-04-28T13:00:00.000Z)."}, status=400)
        if timezone.is_naive(start_slot):
            start_slot = timezone.make_aware(start_slot, timezone.utc)
        end_slot = start_slot + timedelta(minutes=duration)

        # Занятые в этот слот: тренеры с пересекающимися бронями
        busy_coach_ids = set(
            Booking.objects.filter(
                coach_id__isnull=False,
                start_time__lt=end_slot,
                end_time__gt=start_slot,
            ).exclude(status='CANCELED').values_list('coach_id', flat=True)
        )

        coaches = User.objects.filter(
            role__in=['COACH_PADEL', 'COACH_FITNESS']
        ).exclude(id__in=busy_coach_ids).order_by('role', 'first_name', 'last_name')

        from users.serializers import CoachListSerializer
        return Response(CoachListSerializer(coaches, many=True).data)


# ---------------------------------------------------------------------------
# 10. ПРЕВЬЮ ЦЕНЫ С УЧЁТОМ АБОНЕМЕНТА
# ---------------------------------------------------------------------------

class BookingPricePreviewView(APIView):
    """
    POST /api/bookings/price-preview/
    Тело: court_id, start_time (ISO), duration, coach_id?, service_ids (список id).
    Возвращает: total, breakdown, membership_applied, hours_remaining_after.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        court_id = request.data.get('court_id')
        start_time_str = request.data.get('start_time')
        duration = int(request.data.get('duration', 60))
        coach_id = request.data.get('coach_id')
        service_ids = request.data.get('service_ids') or []

        if not court_id or not start_time_str:
            return Response(
                {"error": "Укажите court_id и start_time."},
                status=400,
            )

        start_time = parse_datetime(start_time_str)
        if start_time is None:
            return Response({"error": "Неверный формат start_time (ожидается ISO)."}, status=400)
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.utc)

        court = get_object_or_404(Court, pk=court_id)
        end_time = start_time + timedelta(minutes=duration)
        hours = Decimal(str(duration / 60))
        user = request.user

        # Абонемент PADEL
        active_membership = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            end_date__gte=timezone.now(),
            hours_remaining__gte=hours,
            membership_type__service_type='PADEL',
        ).order_by('end_date').first()

        paid_by_membership = bool(active_membership)
        hours_remaining_after = None
        if active_membership:
            hours_remaining_after = float(active_membership.hours_remaining) - float(hours)

        base_court = Decimal(str(court.price_per_hour)) * hours
        final_court = Decimal('0') if paid_by_membership else base_court

        coach_price = Decimal('0')
        if coach_id:
            coach = User.objects.filter(
                id=coach_id,
                role__in=['COACH_PADEL', 'COACH_FITNESS'],
            ).first()
            if coach and getattr(coach, 'price_per_hour', None):
                coach_price = Decimal(str(coach.price_per_hour)) * hours

        services_price = Decimal('0')
        for sid in service_ids:
            try:
                svc = Service.objects.get(id=sid, is_active=True)
                services_price += Decimal(str(svc.price))
            except Service.DoesNotExist:
                pass

        total = final_court + coach_price + services_price
        breakdown = {
            "court": float(final_court),
            "coach": float(coach_price),
            "services": float(services_price),
        }

        return Response({
            "total": float(total),
            "breakdown": breakdown,
            "membership_applied": paid_by_membership,
            "hours_remaining_after": round(hours_remaining_after, 1) if hours_remaining_after is not None else None,
            "membership_name": active_membership.membership_type.name if active_membership else None,
        })
