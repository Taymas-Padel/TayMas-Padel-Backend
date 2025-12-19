from django.contrib import admin
from .models import Booking, BookingService

class BookingServiceInline(admin.TabularInline):
    model = BookingService
    extra = 0 # Чтобы не показывать пустые строчки лишний раз

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'court', 'start_time', 'end_time', 'price', 'status', 'coach')
    # БЫЛО: list_filter = ('status', 'court', 'date')
    # СТАЛО (исправлено):
    list_filter = ('status', 'court', 'start_time') 
    
    inlines = [BookingServiceInline]