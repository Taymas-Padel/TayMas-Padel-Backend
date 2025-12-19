from django.contrib import admin
from .models import ClubSetting, ClosedDay # <--- Добавили ClosedDay

@admin.register(ClubSetting)
class ClubSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description')
    list_editable = ('value',)

# --- НОВОЕ ---
@admin.register(ClosedDay)
class ClosedDayAdmin(admin.ModelAdmin):
    list_display = ('date', 'reason')
    list_filter = ('date',)