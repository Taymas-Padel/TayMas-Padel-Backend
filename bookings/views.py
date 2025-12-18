from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import make_aware, localtime # <--- ВАЖНО: Добавили localtime
from datetime import datetime, time
from .models import Booking
from .serializers import SlotAvailabilitySerializer, CreateBookingSerializer
from rest_framework import generics, permissions
from .serializers import BookingSerializer
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

class CancelBookingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # 1. Ищем бронирование по ID (pk)
        booking = get_object_or_404(Booking, pk=pk)

        # 2. Проверяем, владелец ли это (или админ)
        if booking.client != request.user and not request.user.is_staff:
            raise PermissionDenied("Вы не можете отменить чужое бронирование.")

        # 3. Проверяем, не отменено ли уже
        if booking.status == Booking.Status.CANCELED:
            return Response(
                {"detail": "Это бронирование уже отменено."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Меняем статус
        booking.status = Booking.Status.CANCELED
        booking.save()

        return Response({"status": "Бронирование отменено"}, status=status.HTTP_200_OK)

class UserBookingsListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Если админ - видит всё
        if user.is_staff:
            return Booking.objects.all().order_by('-start_time')
        # Если обычный смертный - только свои
        return Booking.objects.filter(client=user).order_by('-start_time')
    

class CreateBookingView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = CreateBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

class CheckAvailabilityView(APIView):
    def get(self, request):
        serializer = SlotAvailabilitySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        court_id = serializer.validated_data['court_id']
        date_obj = serializer.validated_data['date']

        # Границы рабочего дня
        day_start = make_aware(datetime.combine(date_obj, time(7, 0)))
        day_end = make_aware(datetime.combine(date_obj, time(23, 0)))

        bookings = Booking.objects.filter(
            court_id=court_id,
            end_time__gt=day_start, 
            start_time__lt=day_end 
        ).exclude(status='CANCELED')

        busy_slots = []
        for b in bookings:
            # 1. Переводим время из UTC в локальное (например, в Астану)
            local_start = localtime(b.start_time)
            local_end = localtime(b.end_time)

            # 2. Обрезаем по границам дня (сравниваем с day_start/end)
            # Важно: day_start уже с часовым поясом, так что всё ок
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
            "busy_slots": busy_slots
        })