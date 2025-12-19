from django.contrib import admin
from .models import Court

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    # Добавили 'id' в самое начало списка
    list_display = ('id', 'name', 'court_type', 'price_per_hour', 'is_active')
    
    list_filter = ('court_type', 'is_active')
    search_fields = ('name',)