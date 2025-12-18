from rest_framework import serializers
from .models import Court

class CourtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Court
        # Какие поля отдавать мобилке
        fields = ['id', 'name', 'description', 'price_per_hour', 'image', 'is_active']