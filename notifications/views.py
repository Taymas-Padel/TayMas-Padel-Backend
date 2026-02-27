from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/?unread=true&type=BOOKING
    Список уведомлений текущего пользователя.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread = self.request.query_params.get('unread')
        ntype = self.request.query_params.get('type')
        if unread == 'true':
            qs = qs.filter(is_read=False)
        if ntype:
            qs = qs.filter(notification_type=ntype.upper())
        return qs


class NotificationUnreadCountView(APIView):
    """
    GET /api/notifications/unread-count/
    Количество непрочитанных уведомлений (для бейджа).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/<id>/read/ — пометить как прочитанное.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        n = Notification.objects.filter(pk=pk, user=request.user).first()
        if not n:
            return Response({"detail": "Не найдено."}, status=404)
        n.is_read = True
        n.save(update_fields=['is_read'])
        return Response({"status": "ok"})


class NotificationMarkAllReadView(APIView):
    """
    POST /api/notifications/read-all/ — отметить все как прочитанные.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"marked_read": count})


class NotificationDeleteView(APIView):
    """
    DELETE /api/notifications/<id>/ — удалить уведомление.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = Notification.objects.filter(pk=pk, user=request.user).delete()
        if not deleted:
            return Response({"detail": "Не найдено."}, status=404)
        return Response(status=204)
