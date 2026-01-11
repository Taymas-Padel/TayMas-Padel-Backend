from rest_framework import serializers
from .models import FriendRequest
from django.contrib.auth import get_user_model

User = get_user_model()

class UserShortSerializer(serializers.ModelSerializer):
    """Краткая инфа о пользователе для списка друзей"""
    class Meta:
        model = User
        fields = ['id', 'username', 'phone_number', 'first_name', 'last_name']

class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserShortSerializer(read_only=True)
    to_user = UserShortSerializer(read_only=True)
    
    # Для создания запроса нам нужен только ID получателя
    to_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'from_user', 'to_user', 'to_user_id', 'status', 'created_at']
        read_only_fields = ['status', 'from_user', 'to_user']

    def create(self, validated_data):
        to_user_id = validated_data.pop('to_user_id')
        from_user = self.context['request'].user

        # Проверка: существует ли такой юзер
        try:
            target_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден.")

        if from_user == target_user:
            raise serializers.ValidationError("Нельзя добавить себя.")

        # Проверка: может заявка уже есть?
        if FriendRequest.objects.filter(from_user=from_user, to_user=target_user).exists():
            raise serializers.ValidationError("Заявка уже отправлена.")
            
        # Проверка: может они уже друзья (зеркально)?
        if FriendRequest.objects.filter(from_user=target_user, to_user=from_user, status='ACCEPTED').exists():
            raise serializers.ValidationError("Вы уже друзья.")

        return FriendRequest.objects.create(from_user=from_user, to_user=target_user, **validated_data)
    
class FriendRequestActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'reject'])