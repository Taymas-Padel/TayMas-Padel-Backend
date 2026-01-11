from rest_framework import generics
from django.utils import timezone
from .models import Promotion
from .serializers import PromotionSerializer

class ActivePromotionsView(generics.ListAPIView):
    """Возвращает список акций, которые идут прямо сейчас"""
    serializer_class = PromotionSerializer
    permission_classes = [] # Открыто для всех (даже без логина)

    def get_queryset(self):
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )