from django.contrib import admin
from .models import Court, CourtImage

# Это позволит добавлять фото прямо внутри страницы Корта
class CourtImageInline(admin.TabularInline):
    model = CourtImage
    extra = 3  # Сколько пустых полей показывать сразу

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    # Добавили 'id' в самое начало списка
    list_display = ('id', 'name', 'court_type', 'price_per_hour', 'is_active')
    inlines = [CourtImageInline]  # <--- Подключаем галерею
    list_filter = ('court_type', 'is_active')
    search_fields = ('name',)