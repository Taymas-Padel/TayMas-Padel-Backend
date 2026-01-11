from rest_framework import serializers
from .models import Promotion

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'title', 'description', 'image_url', 'promo_code', 'discount_type', 'discount_value', 'start_date', 'end_date']