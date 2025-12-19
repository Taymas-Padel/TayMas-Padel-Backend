from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'role', 'phone_number')

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        # Убедись, что rating_elo и price_per_hour есть в этом списке!
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'role', 'phone_number', 'rating_elo', 'avatar', 'price_per_hour')
        ref_name = "CustomUserSerializer"