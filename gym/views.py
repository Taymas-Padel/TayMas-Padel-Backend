from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, generics
from rest_framework.parsers import JSONParser
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import GymVisit, PersonalTraining
from .serializers import ScanQRSerializer, PersonalTrainingSerializer, GymVisitSerializer
from memberships.models import UserMembership
from finance.models import Transaction
from bookings.models import Booking
from users.permissions import IsReceptionist, IsAdminRole

User = get_user_model()
signer = TimestampSigner()


class GenerateQREntryView(APIView):
    """
    GET /api/gym/qr/generate/
    Клиент генерирует QR-код для входа (действует 60 секунд).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        signed_value = signer.sign(str(user_id))
        return Response({
            "qr_content": signed_value,
            "valid_seconds": 60,
            "message": "Покажите этот QR сканеру на входе"
        })


class ScanQREntryView(APIView):
    """
    POST /api/gym/qr/scan/
    Турникет/ресепшн сканирует QR. Проверяет доступ к залу или падел-зоне.
    Только для ADMIN и RECEPTIONIST.
    """
    permission_classes = [IsReceptionist]

    @swagger_auto_schema(request_body=ScanQRSerializer)
    def post(self, request):
        serializer = ScanQRSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        qr_content = serializer.validated_data['qr_content']
        location = serializer.validated_data['location']

        try:
            # QR живёт 60 секунд (max_age=60)
            user_id = signer.unsign(qr_content, max_age=60)
            user = get_object_or_404(User, pk=user_id)
        except SignatureExpired:
            return Response({"status": "DENIED", "error": "QR-код устарел. Попросите сгенерировать новый."}, status=403)
        except BadSignature:
            return Response({"status": "DENIED", "error": "Неверный QR-код."}, status=403)

        # Проверяем блокировку QR
        if user.is_qr_blocked:
            return Response({
                "status": "BLOCKED",
                "error": f"QR-доступ заблокирован для {user.first_name or user.username}. Обратитесь на ресепшн."
            }, status=403)

        now = timezone.now()
        today = now.date()
        access_granted = False
        messages = []

        # ==============================
        # ЛОГИКА ДЛЯ ПАДЕЛА
        # ==============================
        if location in ['PADEL', 'ALL']:
            # 1. Проверяем клубный абонемент (тип PADEL)
            has_padel_membership = UserMembership.objects.filter(
                user=user,
                is_active=True,
                is_frozen=False,
                end_date__gte=now,
                membership_type__service_type__in=['PADEL_HOURS', 'TRAINING_HOURS', 'VIP'],
            ).exists()

            if has_padel_membership:
                access_granted = True
                messages.append("Член клуба (абонемент Падел)")

            # 2. Проверяем бронь на сегодня
            # ИСПРАВЛЕНО: убран несуществующий статус 'PAID'
            today_booking = Booking.objects.filter(
                user=user,
                start_time__date=today,
                end_time__gte=now,
                status__in=['CONFIRMED', 'PENDING']
            ).order_by('start_time').first()

            if today_booking:
                access_granted = True
                start_s = timezone.localtime(today_booking.start_time).strftime('%H:%M')
                end_s = timezone.localtime(today_booking.end_time).strftime('%H:%M')
                messages.append(
                    f"Бронь: Корт {today_booking.court.name} ({start_s}–{end_s})"
                )

        # ==============================
        # ЛОГИКА ДЛЯ ЗАЛА (GYM)
        # ==============================
        if location in ['GYM', 'ALL']:
            gym_sub = UserMembership.objects.filter(
                user=user,
                is_active=True,
                is_frozen=False,
                membership_type__service_type__in=['GYM', 'VIP'],
            ).first()

            if gym_sub:
                has_visits_limit = gym_sub.membership_type.total_visits > 0

                if has_visits_limit:
                    if gym_sub.visits_remaining > 0:
                        if location == 'GYM':
                            gym_sub.visits_remaining -= 1
                            gym_sub.save()
                            GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
                        access_granted = True
                        messages.append(f"Зал: пакет (осталось: {gym_sub.visits_remaining})")
                    else:
                        messages.append("Зал: пакет посещений исчерпан")
                else:
                    if gym_sub.end_date >= now:
                        if location == 'GYM':
                            GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
                        access_granted = True
                        messages.append(
                            f"Зал: безлимит до {timezone.localtime(gym_sub.end_date).strftime('%d.%m.%Y')}"
                        )
                    else:
                        messages.append("Зал: абонемент истёк")

        # Итоговый ответ
        full_name = f"{user.first_name} {user.last_name}".strip()
        display_name = full_name if full_name else (user.phone_number or user.username)

        if access_granted:
            return Response({
                "status": "SUCCESS",
                "user_id": user.id,
                "user": display_name,
                "phone": user.phone_number,
                "is_qr_blocked": user.is_qr_blocked,
                "details": " | ".join(messages)
            })
        else:
            reason = "Нет активного абонемента и брони."
            if location == 'PADEL':
                reason = "Нет активной брони на сегодня и нет членства в клубе."
            elif location == 'GYM':
                reason = "Нет активного абонемента в зал."

            return Response({
                "status": "DENIED",
                "user": display_name,
                "error": reason
            }, status=403)


class GymCheckInView(APIView):
    """
    POST /api/gym/checkin/
    Клиент входит в зал: сначала проверяем абонемент, иначе разовый платеж.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        now = timezone.now()
        ONE_TIME_PRICE = 3000

        # 1. Проверяем безлимит
        gym_sub = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            membership_type__service_type__in=['GYM', 'VIP'],
            end_date__gte=now,
        ).first()

        if gym_sub:
            has_visits_limit = gym_sub.membership_type.total_visits > 0

            if has_visits_limit:
                if gym_sub.visits_remaining > 0:
                    gym_sub.visits_remaining -= 1
                    gym_sub.save()
                    GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
                    return Response({
                        "status": "ACCESS_GRANTED",
                        "type": "PACK",
                        "message": f"Вход по пакету: {gym_sub.membership_type.name}",
                        "visits_remaining": gym_sub.visits_remaining,
                    })
            else:
                GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
                return Response({
                    "status": "ACCESS_GRANTED",
                    "type": "SUBSCRIPTION",
                    "message": f"Вход по абонементу: {gym_sub.membership_type.name}",
                    "valid_until": timezone.localtime(gym_sub.end_date).strftime('%d.%m.%Y'),
                })

        # 3. Разовый платеж (ИСПРАВЛЕНО: правильный transaction_type)
        Transaction.objects.create(
            user=user,
            amount=ONE_TIME_PRICE,
            transaction_type=Transaction.TransactionType.OTHER,
            payment_method=Transaction.PaymentMethod.UNKNOWN,
            description="Разовое посещение зала"
        )
        GymVisit.objects.create(user=user, checkin_type='ONE_TIME')

        return Response({
            "status": "ONE_TIME_PAYMENT",
            "type": "ONE_TIME",
            "message": "Абонемент не найден. Оформлен разовый визит.",
            "price": ONE_TIME_PRICE
        })


class PersonalTrainingListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/gym/personal-training/  — мои тренировки (клиент) или все (тренер/админ)
    POST /api/gym/personal-training/  — записать клиента к тренеру
    """
    serializer_class = PersonalTrainingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'RECEPTIONIST']:
            return PersonalTraining.objects.all().order_by('-start_time')
        if user.role in ['COACH_FITNESS', 'COACH_PADEL']:
            return PersonalTraining.objects.filter(coach=user).order_by('-start_time')
        return PersonalTraining.objects.filter(client=user).order_by('-start_time')

    def perform_create(self, serializer):
        user = self.request.user
        # Клиент создаёт тренировку для себя
        if user.role == 'CLIENT':
            serializer.save(client=user)
        else:
            serializer.save()


class PersonalTrainingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/gym/personal-training/<id>/
    """
    serializer_class = PersonalTrainingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PersonalTraining.objects.none()
        user = self.request.user
        if user.role in ['ADMIN', 'RECEPTIONIST']:
            return PersonalTraining.objects.all()
        if user.role in ['COACH_FITNESS', 'COACH_PADEL']:
            return PersonalTraining.objects.filter(coach=user)
        return PersonalTraining.objects.filter(client=user)


class MyGymVisitsView(generics.ListAPIView):
    """
    GET /api/gym/visits/
    История посещений зала текущего пользователя (для мобилки).
    """
    serializer_class = GymVisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GymVisit.objects.filter(user=self.request.user).order_by('-entry_time')
