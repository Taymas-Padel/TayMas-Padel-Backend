from rest_framework import serializers
from .models import NewsItem


class NewsItemSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = NewsItem
        fields = [
            'id', 'title', 'content', 'category', 'category_label',
            'image_url', 'is_pinned', 'created_at', 'created_at_formatted',
        ]

    def get_category_label(self, obj):
        return obj.get_category_display()

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y')
