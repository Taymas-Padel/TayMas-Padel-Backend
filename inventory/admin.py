from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'group', 'category', 'price', 'is_active')
    list_editable = ('price', 'is_active')
    list_filter = ('group', 'category', 'is_active')
    search_fields = ('name', 'description')