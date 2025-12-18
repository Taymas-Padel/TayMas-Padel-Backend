from rest_framework import serializers
from .models import Booking
from courts.models import Court
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()
class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'court', 'client', 'start_time', 'end_time', 'price', 'is_paid', 'status']
        read_only_fields = ['client', 'price', 'status', 'is_paid'] # Клиент не может сам себе поставить статус "Оплачено"

class SlotAvailabilitySerializer(serializers.Serializer):
    """
    Сериализатор только для проверки свободных мест.
    Принимает дату и ID корта.
    """
    court_id = serializers.IntegerField()
    date = serializers.DateField()

# bookings/serializers.py


# ... ваши другие сериализаторы (BookingSerializer, SlotAvailabilitySerializer) оставьте без изменений ...

class CreateBookingSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(write_only=True)
    # Добавляем поле тренера (необязательное)
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), # В идеале фильтровать по role='COACH'
        required=False, 
        allow_null=True
    )

    class Meta:
        model = Booking
        fields = ['court', 'start_time', 'duration', 'coach'] # <-- Добавили coach

    def validate(self, data):
        court = data['court']
        start_time = data['start_time']
        duration = data['duration']
        coach = data.get('coach') # Получаем тренера, если он есть

        end_time = start_time + timedelta(minutes=duration)

        # 1. ПРОВЕРКА КОРТА (Ваш старый код)
        court_conflicts = Booking.objects.filter(
            court=court,
            status__in=['CONFIRMED', 'PENDING'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        if court_conflicts.exists():
            raise serializers.ValidationError("К сожалению, этот корт уже занят в указанное время.")

        # 2. ПРОВЕРКА ТРЕНЕРА (Новый код)
        if coach:
            coach_conflicts = Booking.objects.filter(
                coach=coach,
                status__in=['CONFIRMED', 'PENDING'],
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            if coach_conflicts.exists():
                raise serializers.ValidationError({
                    "coach": f"Тренер {coach.username} уже занят в это время на другом корте."
                })

        data['end_time'] = end_time
        return data

    def create(self, validated_data):
        duration = validated_data.pop('duration')
        
        court = validated_data['court']
        hours = duration / 60
        price = float(court.price_per_hour) * hours

        # Если выбран тренер, можно накинуть цену (опционально)
        # if validated_data.get('coach'):
        #     price += 5000 * hours 
        
        booking = Booking.objects.create(price=price, **validated_data)
        return booking

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['end_time'] = instance.end_time
        data['price'] = instance.price
        data['status'] = instance.status
        if instance.coach:
            data['coach_name'] = instance.coach.username
        return data
