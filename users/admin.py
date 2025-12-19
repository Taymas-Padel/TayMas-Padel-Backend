from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 1. Поля, которые видны в СПИСКЕ пользователей
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'price_per_hour', 'is_staff')
    
    # 2. Фильтры справа
    list_filter = ('role', 'is_staff', 'is_active')
    
    # 3. Поля, которые видны внутри КАРТОЧКИ пользователя (Редактирование)
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('role', 'phone_number', 'avatar', 'rating_elo', 'price_per_hour')
        }),
    )

    # 4. Поля, которые видны при СОЗДАНИИ пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('email', 'first_name', 'last_name', 'role', 'phone_number', 'price_per_hour')
        }),
    )