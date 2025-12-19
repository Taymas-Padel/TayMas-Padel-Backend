from rest_framework import serializers
from .models import Court

class CourtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Court
        # Добавили 'court_type', чтобы фронтенд знал (Крытый/Открытый)
        fields = ['id', 'name', 'court_type', 'description', 'price_per_hour', 'image', 'is_active']