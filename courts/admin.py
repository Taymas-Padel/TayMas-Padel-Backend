from django.contrib import admin
from .models import Court

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_hour', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)