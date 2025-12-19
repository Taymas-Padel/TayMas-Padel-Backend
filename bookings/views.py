from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, localtime
from django.utils import timezone 
from datetime import datetime, time

# --- ИМПОРТЫ НАШИХ МОДЕЛЕЙ ---
from .models import Booking
from .serializers import BookingSerializer, CreateBookingSerializer, SlotAvailabilitySerializer
from finance.models import Transaction  # <--- Чтобы возвращать деньги
from core.models import ClubSetting     # <--- Чтобы знать правила отмены

# 1. ОТМЕНА БРОНИ (С умной логикой)
class CancelBookingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)

        # Проверка: владелец (user) или админ
        if booking.user != request.user and not request.user.is_staff:
            raise PermissionDenied("Вы не можете отменить чужое бронирование.")

        # Если уже отменена - стоп
        if booking.status == 'CANCELED':
            return Response({"detail": "Это бронирование уже отменено."}, status=status.HTTP_400_BAD_REQUEST)

        # --- НАЧАЛО: ПРОВЕРКА ВРЕМЕНИ (из Настроек) ---
        # 1. Достаем настройку из базы (если нет - дефолт 24 часа)
        setting = ClubSetting.objects.filter(key='CANCELLATION_HOURS').first()
        limit_hours = int(setting.value) if setting else 24

        # 2. Считаем, сколько часов осталось до начала игры
        time_until_match = booking.start_time - timezone.now()
        hours_left = time_until_match.total_seconds() / 3600

        # 3. Если времени мало — запрещаем (только если это не Админ)
        # Админу разрешаем отменять всегда (is_staff)
        if hours_left < limit_hours and not request.user.is_staff:
             return Response(
                {"detail": f"Отмена невозможна. Правила клуба: минимум за {limit_hours} ч."}, 
                status=status.HTTP_400_BAD_REQUEST
             )
        # --- КОНЕЦ ПРОВЕРКИ ---

        # Отменяем
        booking.status = 'CANCELED'  # Убедись, что в модели статус называется именно так (или 'CANCELLED')
        booking.save()

        # --- ВОЗВРАТ ДЕНЕГ (FINANCE) ---
        # Создаем транзакцию с минусом, чтобы баланс сошелся
        Transaction.objects.create(
            user=booking.user,
            booking=booking,
            amount=-booking.price,  # Возвращаем сумму
            transaction_type='REFUND',
            description=f"Возврат за отмену брони #{booking.id}"
        )

        return Response({"status": "Бронирование отменено, средства возвращены"}, status=status.HTTP_200_OK)


# 2. СПИСОК БРОНЕЙ (Тут всё ок)
class UserBookingsListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.all().order_by('-start_time')
        return Booking.objects.filter(user=user).order_by('-start_time')


# 3. СОЗДАНИЕ БРОНИ (Тут всё ок, валидация внутри сериализатора)
class CreateBookingView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = CreateBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# 4. ПРОВЕРКА СЛОТОВ (Улучшили: теперь берет время работы из настроек)
class CheckAvailabilityView(APIView):
    def get(self, request):
        serializer = SlotAvailabilitySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        court_id = serializer.validated_data['court_id']
        date_obj = serializer.validated_data['date']

        # --- Берем реальное время работы клуба ---
        open_conf = ClubSetting.objects.filter(key='OPEN_TIME').first()
        close_conf = ClubSetting.objects.filter(key='CLOSE_TIME').first()
        
        open_h = int(open_conf.value.split(':')[0]) if open_conf else 7
        close_h = int(close_conf.value.split(':')[0]) if close_conf else 23

        # Формируем границы дня
        day_start = make_aware(datetime.combine(date_obj, time(open_h, 0)))
        day_end = make_aware(datetime.combine(date_obj, time(close_h, 0)))

        # Ищем занятые слоты
        bookings = Booking.objects.filter(
            court_id=court_id,
            end_time__gt=day_start, 
            start_time__lt=day_end 
        ).exclude(status='CANCELED')

        busy_slots = []
        for b in bookings:
            local_start = localtime(b.start_time)
            local_end = localtime(b.end_time)
            # Обрезаем бронь по границам рабочего дня (на всякий случай)
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
            "work_hours": f"{open_h}:00 - {close_h}:00", # Полезно для фронта
            "busy_slots": busy_slots
        })