from django.contrib import admin
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'is_active')
    list_editable = ('price', 'is_active') # Чтобы менять цену прямо в списке