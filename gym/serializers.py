from rest_framework import serializers
from .models import GymVisit, PersonalTraining
from django.contrib.auth import get_user_model

User = get_user_model()


class ScanQRSerializer(serializers.Serializer):
    qr_content = serializers.CharField(help_text="Зашифрованная строка QR-кода")
    LOCATION_CHOICES = [
        ('GYM', 'Турникет зала'),
        ('PADEL', 'Ресепшн падела'),
        ('ALL', 'Общий вход'),
    ]
    location = serializers.ChoiceField(choices=LOCATION_CHOICES, default='ALL')


class GymVisitSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    entry_time_formatted = serializers.SerializerMethodField()

    class Meta:
        model = GymVisit
        fields = ['id', 'user', 'user_name', 'entry_time', 'entry_time_formatted', 'checkin_type']
        read_only_fields = ['entry_time']

    def get_user_name(self, obj):
        full = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full or obj.user.phone_number or obj.user.username

    def get_entry_time_formatted(self, obj):
        return obj.entry_time.strftime('%d.%m.%Y %H:%M') if obj.entry_time else None


class PersonalTrainingSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    coach_name = serializers.SerializerMethodField()

    class Meta:
        model = PersonalTraining
        fields = [
            'id', 'client', 'client_name', 'coach', 'coach_name',
            'start_time', 'price', 'is_paid', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_client_name(self, obj):
        full = f"{obj.client.first_name} {obj.client.last_name}".strip()
        return full or obj.client.phone_number or obj.client.username

    def get_coach_name(self, obj):
        full = f"{obj.coach.first_name} {obj.coach.last_name}".strip()
        return full or obj.coach.phone_number or obj.coach.username

    def validate_coach(self, value):
        if value.role not in ['COACH_FITNESS', 'COACH_PADEL', 'ADMIN']:
            raise serializers.ValidationError("Выбранный пользователь не является тренером.")
        return value
