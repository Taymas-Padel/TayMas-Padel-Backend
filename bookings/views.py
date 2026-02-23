from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, localtime
from django.utils import timezone 
from datetime import datetime, time
from django.db import transaction # 👈 ВАЖНЫЙ ИМПОРТ ДЛЯ ТРАНЗАКЦИЙ
from django.db.models import Q # <--- Добавь этот импорт наверху
# --- ИМПОРТЫ НАШИХ МОДЕЛЕЙ ---
from .models import Booking
from .serializers import BookingSerializer, CreateBookingSerializer, SlotAvailabilitySerializer
from finance.models import Transaction
from .serializers import ManagerScheduleSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from courts.models import Court
from core.models import ClubSetting, ClosedDay
# 1. ОТМЕНА БРОНИ (Твой код без изменений)
# ... импорты остаются те же ...

# 1. ОТМЕНА БРОНИ
class CancelBookingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        user = request.user
        now = timezone.now()

        # 1. Проверка: Это хозяин брони? (Админу можно)
        if booking.user != user and not user.is_staff:
            return Response({"detail": "Вы не можете отменить чужую бронь."}, status=403)

        # 2. Проверка: Бронь уже отменена?
        if booking.status == 'CANCELED':
            return Response({"detail": "Бронирование уже отменено."}, status=400)

        # 3. Проверка: Игра уже прошла или идет?
        if booking.start_time <= now:
            return Response({"detail": "Нельзя отменить прошедшее бронирование."}, status=400)

        # --- ГЛАВНАЯ ПРОВЕРКА 24 ЧАСА ---
        setting = ClubSetting.objects.filter(key='CANCELLATION_HOURS').first()
        limit_hours = int(setting.value) if setting else 24
        
        time_diff = booking.start_time - now
        hours_left = time_diff.total_seconds() / 3600
        
        if hours_left < limit_hours:
            if not user.is_staff:
                return Response(
                    {"detail": f"Поздно! Отмена возможна только за {limit_hours} ч."}, 
                    status=400
                )

        # 4. Сама отмена
        booking.status = 'CANCELED'
        booking.save()

        # 5. Возврат денег (🔥 ОБНОВЛЕННАЯ ТРАНЗАКЦИЯ)
        # Если бронь была бесплатной или еще не оплачена - возврат делать не надо
        if booking.price > 0 and booking.is_paid:
            Transaction.objects.create(
                user=booking.user,
                
                # Ссылка на бронь
                booking=booking, 
                
                # Сумма с минусом (деньги уходят от нас)
                amount=-booking.price, 
                
                # 🔥 НОВЫЕ ПОЛЯ ИЗ MODEL.PY
                transaction_type=Transaction.TransactionType.REFUND,
                payment_method=Transaction.PaymentMethod.UNKNOWN, # Или CASH, смотря как возвращаете
                
                description=f"Возврат: отмена брони #{booking.id}"
            )

        return Response({"status": "Успешно отменено"}, status=200)

# 2. СПИСОК БРОНЕЙ (Твой код без изменений)
class UserBookingsListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Если админ - видит всё
        if user.is_staff:
            return Booking.objects.all().order_by('-start_time')
            
        # 🔥 ИЗМЕНЕННАЯ ЛОГИКА
        # Показываем бронь, ЕСЛИ (ты создатель) ИЛИ (ты в списке участников)
        # .distinct() нужен, чтобы не было дублей, если вдруг что-то пойдет не так
        return Booking.objects.filter(
            Q(user=user) | Q(participants=user)
        ).exclude(status='CANCELED').distinct().order_by('-start_time')


# 3. СОЗДАНИЕ БРОНИ (🔥 ВОТ ЗДЕСЬ ВНЕДРЯЕМ ЗАЩИТУ 🔥)
class CreateBookingView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = CreateBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Мы переопределяем метод create, чтобы обернуть всё в транзакцию
    def create(self, request, *args, **kwargs):
        # 1. Получаем ID корта из запроса, чтобы заблокировать его
        court_id = request.data.get('court')
        
        if not court_id:
             return Response({"court": ["Обязательное поле"]}, status=400)

        try:
            # 🔥 НАЧАЛО ЗАЩИТЫ ОТ ДВОЙНОЙ БРОНИ
            with transaction.atomic():
                # 🔒 БЛОКИРУЕМ КОРТ
                # Пока мы внутри этого блока 'with', никто другой не сможет забронировать этот корт.
                # Они встанут в очередь и будут ждать.
                try:
                    Court.objects.select_for_update().get(id=court_id)
                except Court.DoesNotExist:
                    return Response({"detail": "Корт не найден"}, status=404)

                # Теперь запускаем твой стандартный процесс создания.
                # Твой сериализатор проверит занятость внутри .is_valid(),
                # и так как корт заблокирован, проверка будет 100% точной.
                
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            # 🔥 КОНЕЦ ЗАЩИТЫ (Блокировка снята)

        except ValidationError as e:
            # Если сериализатор вернул ошибку валидации (например, занято)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Любая другая ошибка
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# 4. ПРОВЕРКА СЛОТОВ (Твой код без изменений)
class CheckAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('court_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', required=True),
        ],
        responses={200: "Список занятых слотов"}
    )
    def get(self, request):
        serializer = SlotAvailabilitySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        court_id = serializer.validated_data['court_id']
        date_obj = serializer.validated_data['date']

        # 🔥 1. ПРОВЕРКА НА ПРАЗДНИКИ (Добавляем это сюда)
        # Чтобы мобилка знала заранее, что день закрыт
        closed_day = ClosedDay.objects.filter(date=date_obj).first()
        
        if closed_day:
            return Response({
                "court_id": court_id,
                "date": date_obj,
                "work_hours": "Закрыто",  # Фронт покажет "Closed"
                "is_holiday": True,       # Флаг для красивой отрисовки
                "reason": closed_day.reason or "Санитарный день",
                "busy_slots": []          
            })

        # --- Дальше всё как было ---
        open_conf = ClubSetting.objects.filter(key='OPEN_TIME').first()
        close_conf = ClubSetting.objects.filter(key='CLOSE_TIME').first()
        
        open_h = int(open_conf.value.split(':')[0]) if open_conf else 7
        close_h = int(close_conf.value.split(':')[0]) if close_conf else 23

        day_start = make_aware(datetime.combine(date_obj, time(open_h, 0)))
        day_end = make_aware(datetime.combine(date_obj, time(close_h, 0)))

        bookings = Booking.objects.filter(
            court_id=court_id,
            end_time__gt=day_start, 
            start_time__lt=day_end 
        ).exclude(status='CANCELED')

        busy_slots = []
        for b in bookings:
            local_start = localtime(b.start_time)
            local_end = localtime(b.end_time)
            start = max(local_start, day_start)
            end = min(local_end, day_end)
            
            busy_slots.append({
                "start": start.strftime('%H:%M'),
                "end": end.strftime('%H:%M'),
                "booking_id": b.id 
            })

        return Response({
            "court_id": court_id,
            "date": date_obj,
            "work_hours": f"{open_h}:00 - {close_h}:00",
            "is_holiday": False, # Добавим явно, что не праздник
            "busy_slots": busy_slots
        })

class ManagerScheduleView(APIView):
    permission_classes = [permissions.IsAdminUser] # 🔒 Только Персонал

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'date', 
                openapi.IN_QUERY, 
                description="Дата в формате YYYY-MM-DD (по умолчанию сегодня)", 
                type=openapi.TYPE_STRING
            )
        ],
        responses={200: "Список кортов с бронями"}
    )
    def get(self, request):
        # 1. Определяем дату (или сегодня)
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Неверный формат даты. Используйте YYYY-MM-DD"}, status=400)
        else:
            target_date = timezone.now().date()

        # Границы дня
        day_start = make_aware(datetime.combine(target_date, time(0, 0)))
        day_end = make_aware(datetime.combine(target_date, time(23, 59)))

        # 2. Собираем данные по кортам
        courts = Court.objects.all()
        response_data = []

        for court in courts:
            # Ищем брони для этого корта на этот день
            bookings = Booking.objects.filter(
                court=court,
                start_time__gte=day_start,
                start_time__lt=day_end
            ).exclude(status='CANCELED').order_by('start_time')

            # Сериализуем
            serializer = ManagerScheduleSerializer(bookings, many=True)

            response_data.append({
                "court_id": court.id,
                "court_name": court.name,
                "bookings": serializer.data
            })

        return Response({
            "date": target_date,
            "schedule": response_data
        })