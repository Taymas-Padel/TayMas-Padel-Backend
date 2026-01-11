from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from .serializers import ScanQRSerializer       # <--- Наш новый файл
# 👇 ВОТ ЭТА СТРОКА ОЧЕНЬ ВАЖНА
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from drf_yasg.utils import swagger_auto_schema  # <--- Для документации
from .models import GymVisit
from memberships.models import UserMembership
from finance.models import Transaction

from bookings.models import Booking  # Не забудь про Booking

User = get_user_model()
signer = TimestampSigner()

# ... дальше идет твой код классов ...


class GenerateQREntryView(APIView):
    """
    (Для Клиента) Генерирует зашифрованную строку для входа.
    Клиентское приложение само превратит эту строку в картинку QR.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        # Создаем токен: "user_id" + подпись времени
        # Например: "5:1rHZ8s:abcdef..."
        signed_value = signer.sign(str(user_id))
        
        return Response({
            "qr_content": signed_value,
            "valid_seconds": 60, # Код живет 60 секунд
            "message": "Покажите этот код сканеру"
        })
    
class ScanQREntryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @swagger_auto_schema(request_body=ScanQRSerializer)
    def post(self, request):
        serializer = ScanQRSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        qr_content = serializer.validated_data['qr_content']
        location = serializer.validated_data['location']

        try:
            user_id = signer.unsign(qr_content, max_age=600)
            user = get_object_or_404(User, pk=user_id)
            now = timezone.now()
            today = now.date()
            
            access_granted = False
            messages = [] 

            # ==============================
            # 🎾 ЛОГИКА ДЛЯ ПАДЕЛА (PADEL)
            # ==============================
            if location in ['PADEL', 'ALL']:
                
                # 1. ПРОВЕРКА ЧЛЕНСТВА (СТРОГО ПО ТИПУ)
                # Мы ищем только те абонементы, у которых тип услуги явно "PADEL".
                # Абонементы типа GYM_UNLIMITED сюда просто не попадут.
                has_padel_membership = UserMembership.objects.filter(
                    user=user, 
                    is_active=True, 
                    is_frozen=False,
                    membership_type__service_type='PADEL'  # <--- ВОТ ФУНДАМЕНТАЛЬНОЕ ИСПРАВЛЕНИЕ
                ).exists()

                if has_padel_membership:
                    access_granted = True
                    messages.append("✅ Член Клуба (Доступ разрешен)")

                # 2. ПРОВЕРКА БРОНИ (На сегодня)
                today_booking = Booking.objects.filter(
                    user=user,
                    start_time__date=today, # Дата строго сегодня
                    end_time__gte=now,      # Игра еще не закончилась
                    status__in=['CONFIRMED', 'PAID']
                ).order_by('start_time').first()
                
                if today_booking:
                    access_granted = True
                    
                    start_s = today_booking.start_time.strftime('%H:%M')
                    end_s = today_booking.end_time.strftime('%H:%M')
                    
                    diff = today_booking.end_time - today_booking.start_time
                    minutes = int(diff.total_seconds() / 60)
                    
                    info_msg = f"🎾 ПАДЕЛ: Корт №{today_booking.court.id} ({start_s} - {end_s} | {minutes} мин)"
                    
                    if info_msg not in messages:
                        messages.append(info_msg)

            # ==============================
            # 🏋️ ЛОГИКА ДЛЯ ЗАЛА (GYM)
            # ==============================
            if location in ['GYM', 'ALL']:
                # Ищем ТОЛЬКО абонементы типа Фитнес (Безлимит или Пакет)
                gym_sub = UserMembership.objects.filter(
                    user=user, 
                    is_active=True, 
                    is_frozen=False,
                    membership_type__service_type__in=['GYM_UNLIMITED', 'GYM_PACK'] # <--- СТРОГИЙ ФИЛЬТР
                ).first()

                if gym_sub:
                    # Логика GYM_PACK (Списание)
                    if gym_sub.membership_type.service_type == 'GYM_PACK':
                        if gym_sub.visits_remaining > 0:
                            if location == 'GYM': 
                                gym_sub.visits_remaining -= 1
                                gym_sub.save()
                                GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
                                access_granted = True
                                messages.append(f"🏋️ GYM: Вход списан. Осталось: {gym_sub.visits_remaining}")
                            elif location == 'ALL':
                                access_granted = True
                                messages.append(f"🏋️ GYM: Доступен (Осталось: {gym_sub.visits_remaining})")
                        else:
                             if location == 'GYM':
                                messages.append("🏋️ GYM: Посещения закончились!")
                    
                    # Логика GYM_UNLIMITED (Проверка даты)
                    elif gym_sub.membership_type.service_type == 'GYM_UNLIMITED':
                        if gym_sub.end_date >= now:
                            if location == 'GYM':
                                GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
                            
                            access_granted = True
                            messages.append(f"🏋️ GYM: Безлимит до {gym_sub.end_date.strftime('%d.%m')}")

            # --- ИТОГОВЫЙ ОТВЕТ ---
            full_name = f"{user.first_name} {user.last_name}".strip()
            display_name = full_name if full_name else user.username

            if access_granted:
                unique_messages = list(dict.fromkeys(messages))
                return Response({
                    "status": "SUCCESS",
                    "user": display_name,
                    "details": " + ".join(unique_messages)
                })
            else:
                err_text = "Нет доступа."
                if location == 'PADEL': err_text = "Нет активной брони на сегодня или клубного членства."
                if location == 'GYM': err_text = "Нет активного абонемента в Зал."
                
                return Response({"status": "DENIED", "error": err_text}, status=403)

        except SignatureExpired:
            return Response({"error": "QR-код устарел"}, status=403)
        except BadSignature:
            return Response({"error": "Неверный QR-код"}, status=403)

class GymCheckInView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        now = timezone.now()
        
        # Цена разового входа (можно вынести в настройки)
        ONE_TIME_PRICE = 3000 

        # 1. Проверяем БЕЗЛИМИТ (Год, полгода, месяц)
        unlimited_sub = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            membership_type__service_type='GYM_UNLIMITED', # Ищем именно безлимит в зал
            end_date__gte=now
        ).first()

        if unlimited_sub:
            # УСПЕХ: Пускаем бесплатно
            GymVisit.objects.create(user=user, checkin_type='SUBSCRIPTION')
            return Response({
                "status": "ACCESS_GRANTED",
                "message": f"Вход разрешен. Тариф: {unlimited_sub.membership_type.name}",
                "valid_until": unlimited_sub.end_date.strftime('%d.%m.%Y')
            }, status=200)

        # 2. Если абонемента нет -> РАЗОВЫЙ ВХОД (Создаем долг/транзакцию)
        
        # Создаем запись о транзакции
        Transaction.objects.create(
            user=user,
            amount=ONE_TIME_PRICE,
            transaction_type='PAYMENT',
            description="Разовое посещение Gym"
        )
        
        # Создаем визит
        GymVisit.objects.create(user=user, checkin_type='ONE_TIME')

        return Response({
            "status": "ONE_TIME_PAYMENT", 
            "message": "Абонемент не найден. Оформлен разовый визит.",
            "price": ONE_TIME_PRICE
        }, status=200)