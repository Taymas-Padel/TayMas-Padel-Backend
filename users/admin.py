from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Какие поля показывать в списке пользователей
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff')
    
    # По каким полям можно фильтровать справа
    list_filter = ('role', 'is_staff', 'is_active')
    
    # Поиск по имени и телефону
    search_fields = ('username', 'email', 'phone_number')
    
    # Добавляем наши поля (role, phone, avatar) в форму редактирования
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone_number', 'avatar', 'rating_elo')}),
    )