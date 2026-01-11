from rest_framework import serializers
from .models import Court, CourtImage

class CourtImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourtImage
        fields = ['id', 'image']

class CourtSerializer(serializers.ModelSerializer):
    gallery = CourtImageSerializer(many=True, read_only=True)
    class Meta:
        model = Court
        # 👇 НО ТУТ ЕГО НЕ ХВАТАЛО. Добавь 'gallery' в этот список:
        fields = [
            'id', 
            'name', 
            'court_type', 
            'description', 
            'price_per_hour', 
            'image', 
            'gallery', # <--- ВОТ ЗДЕСЬ ОНО ДОЛЖНО БЫТЬ
            'is_active'
        ]