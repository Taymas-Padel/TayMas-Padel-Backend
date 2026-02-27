from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()
    type_label = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'type_label', 'title', 'body',
            'is_read', 'data', 'created_at', 'time_ago',
        ]

    def get_time_ago(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        if delta.seconds < 60:
            return "только что"
        if delta.seconds < 3600:
            return f"{delta.seconds // 60} мин назад"
        if delta.days == 0:
            return f"{delta.seconds // 3600} ч назад"
        if delta.days == 1:
            return "вчера"
        return obj.created_at.strftime('%d.%m.%Y')
