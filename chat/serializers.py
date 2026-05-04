from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class _ChatUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'avatar', 'phone_number']

    def get_full_name(self, obj):
        if obj.first_name or obj.last_name:
            return f'{obj.first_name} {obj.last_name}'.strip()
        return obj.phone_number or obj.username


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender_id', 'text',
            'status', 'is_read', 'client_message_id', 'created_at',
        ]
        read_only_fields = ['id', 'conversation', 'sender_id', 'status', 'is_read', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    companion = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'companion', 'last_message', 'unread_count', 'updated_at']

    def _get_companion(self, obj):
        me = self.context['request'].user
        return obj.user2 if obj.user1_id == me.id else obj.user1

    def get_companion(self, obj):
        return _ChatUserSerializer(self._get_companion(obj), context=self.context).data

    def get_last_message(self, obj):
        # TAY-10: используем аннотированные значения из queryset — без N+1
        last_id = getattr(obj, 'last_msg_id', None)
        if last_id:
            return {
                'id': last_id,
                'text': getattr(obj, 'last_msg_text', None),
                'sender_id': getattr(obj, 'last_msg_sender_id', None),
                'created_at': getattr(obj, 'last_msg_created_at', None),
                'is_read': getattr(obj, 'last_msg_is_read', None),
                'status': getattr(obj, 'last_msg_status', 'sent'),
            }
        # Fallback для случаев когда объект загружен без аннотаций
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {
                'id': msg.id,
                'text': msg.text,
                'sender_id': msg.sender_id,
                'created_at': msg.created_at,
                'is_read': msg.is_read,
                'status': msg.status,
            }
        return None

    def get_unread_count(self, obj):
        # TAY-10: аннотированное значение без N+1
        if hasattr(obj, 'unread_count_annotated'):
            return obj.unread_count_annotated
        me = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=me).count()
