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