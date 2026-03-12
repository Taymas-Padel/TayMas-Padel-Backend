from django.contrib import admin
from .models import Court, CourtImage, CourtPriceSlot


class CourtImageInline(admin.TabularInline):
    model = CourtImage
    extra = 3


class CourtPriceSlotInline(admin.TabularInline):
    model = CourtPriceSlot
    extra = 2
    fields = ('start_time', 'end_time', 'price_per_hour')
    help_text = "Задайте временные ценовые слоты. 00:00 в поле 'Конец слота' = полночь (конец суток)."


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'court_type', 'play_format', 'price_per_hour', 'is_active')
    list_filter = ('court_type', 'play_format', 'is_active')
    search_fields = ('name',)
    inlines = [CourtPriceSlotInline, CourtImageInline]


@admin.register(CourtPriceSlot)
class CourtPriceSlotAdmin(admin.ModelAdmin):
    list_display = ('court', 'start_time', 'end_time', 'price_per_hour')
    list_filter = ('court',)
