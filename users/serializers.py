from rest_framework import serializers
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

# --- Стандартные (для Djoser/Admin) ---
class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'phone_number')

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'role', 'phone_number', 'rating_elo', 'avatar', 'price_per_hour', 'is_qr_blocked')
        
        # 🔥 first_name и last_name здесь НЕТ, чтобы их можно было заполнить в первый раз
        read_only_fields = ('email', 'username', 'role', 'rating_elo', 'price_per_hour', 'phone_number', 'is_qr_blocked')
        
        ref_name = "CustomUserSerializer"

    # 🔥 ЗАЩИТА: Разрешаем менять Имя, только если оно пустое
    def validate_first_name(self, value):
        user = self.instance
        if user and user.first_name: # Если имя уже есть
            if user.first_name != value: # И пытаются поставить другое
                raise serializers.ValidationError("Изменение имени запрещено. Обратитесь к администратору.")
        return value

    # 🔥 ЗАЩИТА: То же самое для Фамилии
    def validate_last_name(self, value):
        user = self.instance
        if user and user.last_name:
            if user.last_name != value:
                raise serializers.ValidationError("Изменение фамилии запрещено. Обратитесь к администратору.")
        return value

# --- 👇 НОВЫЕ (для СМС Входа) ---
class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

class VerifyCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=4)
    # 🔥 Теперь требуем ID устройства при входе
    device_id = serializers.CharField(max_length=255, required=True)



class UserPublicSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # ВАЖНО: Сюда пишем только публичные поля. 
        # QR-код, email, телефон сюда НЕ добавляем!
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']

