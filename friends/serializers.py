from rest_framework import serializers
from .models import FriendRequest
from django.contrib.auth import get_user_model

User = get_user_model()


class UserShortSerializer(serializers.ModelSerializer):
    """Публичные данные — БЕЗ телефона"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']


class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserShortSerializer(read_only=True)
    to_user = UserShortSerializer(read_only=True)
    to_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'from_user', 'to_user', 'to_user_id', 'status', 'created_at']
        read_only_fields = ['status', 'from_user', 'to_user']

    def create(self, validated_data):
        to_user_id = validated_data.pop('to_user_id')
        from_user = self.context['request'].user

        try:
            target_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден.")

        if from_user == target_user:
            raise serializers.ValidationError("Нельзя добавить себя.")

        # Проверка в обе стороны
        existing = FriendRequest.objects.filter(
            from_user=from_user, to_user=target_user
        ).first()

        if existing:
            if existing.status == 'REJECTED':
                # Повторная заявка после отклонения — сбрасываем в PENDING
                existing.status = 'PENDING'
                existing.save()
                return existing
            elif existing.status == 'ACCEPTED':
                raise serializers.ValidationError("Вы уже друзья.")
            else:
                raise serializers.ValidationError("Заявка уже отправлена.")

        if FriendRequest.objects.filter(
            from_user=target_user, to_user=from_user, status='ACCEPTED'
        ).exists():
            raise serializers.ValidationError("Вы уже друзья.")

        return FriendRequest.objects.create(
            from_user=from_user, to_user=target_user, **validated_data
        )


class FriendRequestActionSerializer(serializers.Serializer):
    """Принять / Отклонить"""
    request_id = serializers.IntegerField(help_text="ID заявки")
    action = serializers.ChoiceField(choices=['accept', 'reject'])