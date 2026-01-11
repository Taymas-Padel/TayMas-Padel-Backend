from django.contrib import admin
from .models import FriendRequest

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    # Добавляем 'id' в самое начало списка
    list_display = ('id', 'from_user', 'to_user', 'status', 'created_at') 
    
    # Делаем так, чтобы при клике на ID открывалась заявка
    list_display_links = ('id', 'from_user') 
    
    list_filter = ('status',)
    search_fields = ('from_user__username', 'to_user__username')