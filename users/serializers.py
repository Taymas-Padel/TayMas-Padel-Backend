from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from .models import User
# If you are inheriting from Djoser, it might look like this:
from djoser.serializers import UserSerializer as BaseUserSerializer

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        # Поля, которые клиент отправляет при регистрации
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'phone_number')

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        # Поля, которые клиент видит в своем профиле
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'rating_elo', 'avatar')
        ref_name = "CustomUserSerializer"