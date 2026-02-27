from rest_framework import serializers
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================
# DJOSER — Стандартные сериализаторы
# =============================================

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'phone_number')


class UserSerializer(BaseUserSerializer):
    is_profile_complete = serializers.BooleanField(read_only=True)

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'phone_number', 'rating_elo', 'avatar',
            'price_per_hour', 'is_qr_blocked', 'is_profile_complete',
        )
        read_only_fields = (
            'email', 'username', 'role', 'rating_elo',
            'price_per_hour', 'phone_number', 'is_qr_blocked',
        )
        ref_name = "CustomUserSerializer"

    def validate_first_name(self, value):
        """Разрешаем менять имя, только если оно пустое"""
        user = self.instance
        if user and user.first_name and user.first_name != value:
            raise serializers.ValidationError(
                "Изменение имени запрещено. Обратитесь к администратору."
            )
        return value

    def validate_last_name(self, value):
        """Разрешаем менять фамилию, только если она пустая"""
        user = self.instance
        if user and user.last_name and user.last_name != value:
            raise serializers.ValidationError(
                "Изменение фамилии запрещено. Обратитесь к администратору."
            )
        return value


# =============================================
# SMS-вход (мобильное приложение)
# =============================================

class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)


class VerifyCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6, min_length=6)  # 6-значный код
    device_id = serializers.CharField(max_length=255, required=True)


# =============================================
# CRM-вход (ресепшн / админ — по паролю)
# =============================================

class CRMLoginSerializer(serializers.Serializer):
    """Вход в CRM по username (или телефону) + пароль"""
    username = serializers.CharField(
        max_length=150,
        help_text="Username или номер телефона"
    )
    password = serializers.CharField(max_length=128)


# =============================================
# Публичный поиск (для приложения — друзья)
# =============================================

class UserPublicSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Только публичные данные — без телефона, QR, email
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']


# =============================================
# Ресепшн — расширенный просмотр клиента
# =============================================

class ReceptionistUserSerializer(serializers.ModelSerializer):
    is_profile_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'phone_number', 'first_name', 'last_name',
            'avatar', 'is_qr_blocked', 'last_device_id', 'role',
            'rating_elo', 'is_profile_complete', 'created_at',
        )
        read_only_fields = fields


class CoachListSerializer(serializers.ModelSerializer):
    """Список тренеров для выбора в брони (имя, роль, цена)."""
    full_name = serializers.SerializerMethodField()
    coach_price = serializers.DecimalField(source='price_per_hour', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'full_name', 'role', 'coach_price', 'phone_number', 'avatar')

    def get_full_name(self, obj):
        full = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full or obj.username or f"Тренер #{obj.id}"


def _get_league(elo):
    """Возвращает словарь с данными лиги по ELO."""
    if elo < 1000:
        return {"name": "Новичок", "min_elo": 0, "max_elo": 999, "color": "#78909c"}
    elif elo < 1200:
        return {"name": "Бронза", "min_elo": 1000, "max_elo": 1199, "color": "#cd7f32"}
    elif elo < 1400:
        return {"name": "Серебро", "min_elo": 1200, "max_elo": 1399, "color": "#9e9e9e"}
    elif elo < 1600:
        return {"name": "Золото", "min_elo": 1400, "max_elo": 1599, "color": "#ffd700"}
    elif elo < 1800:
        return {"name": "Платина", "min_elo": 1600, "max_elo": 1799, "color": "#00bcd4"}
    else:
        return {"name": "Элита", "min_elo": 1800, "max_elo": 9999, "color": "#e91e63"}


class PublicUserProfileSerializer(serializers.ModelSerializer):
    """Публичный профиль пользователя для просмотра другом."""
    full_name = serializers.SerializerMethodField()
    league = serializers.SerializerMethodField()
    matches_played = serializers.SerializerMethodField()
    matches_won = serializers.SerializerMethodField()
    total_bookings = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'avatar', 'rating_elo', 'league', 'role',
            'matches_played', 'matches_won', 'total_bookings',
        )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_league(self, obj):
        return _get_league(obj.rating_elo)

    def get_matches_played(self, obj):
        from gamification.models import Match
        from django.db.models import Q
        return Match.objects.filter(Q(team_a=obj) | Q(team_b=obj)).distinct().count()

    def get_matches_won(self, obj):
        from gamification.models import Match
        from django.db.models import Q
        return Match.objects.filter(
            Q(team_a=obj, winner_team='A') | Q(team_b=obj, winner_team='B')
        ).distinct().count()

    def get_total_bookings(self, obj):
        from bookings.models import Booking
        from django.db.models import Q
        return Booking.objects.filter(
            Q(user=obj) | Q(participants=obj)
        ).exclude(status='CANCELED').distinct().count()