from rest_framework import serializers
from .models import Court, CourtImage, CourtPriceSlot


class CourtImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourtImage
        fields = ['id', 'image']


class CourtPriceSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourtPriceSlot
        fields = ['id', 'start_time', 'end_time', 'price_per_hour']


class CourtSerializer(serializers.ModelSerializer):
    gallery = CourtImageSerializer(many=True, read_only=True)
    price_slots = CourtPriceSlotSerializer(many=True, read_only=True)

    class Meta:
        model = Court
        fields = [
            'id',
            'name',
            'court_type',
            'play_format',
            'description',
            'price_per_hour',
            'price_slots',
            'image',
            'gallery',
            'is_active',
        ]
