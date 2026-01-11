from django.contrib import admin
from .models import Promotion

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('title', 'promo_code', 'discount_value', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('title', 'promo_code')