from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import Promotion
from .serializers import PromotionSerializer
from users.permissions import IsAdminRole


class ValidatePromoView(APIView):
    """
    GET /api/marketing/validate-promo/?code=XXX
    Проверка промокода без применения. Для отображения скидки в форме брони.
    Возвращает: { "valid": true, "title", "discount_type", "discount_value" } или { "valid": false, "error": "..." }.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        code = (request.query_params.get('code') or '').strip()
        if not code:
            return Response({"valid": False, "error": "Укажите код"})
        now = timezone.now()
        try:
            promo = Promotion.objects.get(
                promo_code__iexact=code,
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
            )
            return Response({
                "valid": True,
                "title": promo.title,
                "discount_type": promo.discount_type,
                "discount_value": float(promo.discount_value),
                "description": promo.description,
            })
        except Promotion.DoesNotExist:
            return Response({"valid": False, "error": "Промокод не найден или недействителен"})


class ActivePromotionsView(generics.ListAPIView):
    """GET /api/marketing/promos/ — акции, которые идут сейчас (для всех)."""
    serializer_class = PromotionSerializer
    permission_classes = []

    def get_queryset(self):
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
        ).order_by('-priority', '-start_date')


class PromotionManageView(generics.ListCreateAPIView):
    """GET/POST /api/marketing/manage/ — список и создание акций (ADMIN)."""
    queryset = Promotion.objects.all().order_by('-priority', '-start_date')
    serializer_class = PromotionSerializer
    permission_classes = [IsAdminRole]


class PromotionManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/marketing/manage/<id>/ — редактирование акции (ADMIN)."""
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAdminRole]