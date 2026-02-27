from django.contrib import admin
from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_published', 'is_pinned', 'created_at']
    list_filter = ['category', 'is_published', 'is_pinned']
    search_fields = ['title', 'content']
    list_editable = ['is_published', 'is_pinned']
