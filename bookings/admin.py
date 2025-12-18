from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('court', 'start_time', 'duration_minutes', 'client', 'price', 'is_paid', 'status')
    list_filter = ('status', 'is_paid', 'court', 'start_time')
    search_fields = ('client__username', 'client__email', 'client__phone_number')
    autocomplete_fields = ['client', 'court'] # Удобный поиск, если клиентов будет 1000+