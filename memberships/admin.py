from django.contrib import admin
from .models import MembershipType, UserMembership

@admin.register(MembershipType)
class MembershipTypeAdmin(admin.ModelAdmin):
    # Что показываем в таблице
    list_display = ('name', 'price', 'total_hours', 'days_valid', 'is_active')
    
    # Что можно менять прямо в списке (не заходя внутрь)
    list_editable = ('price', 'is_active')
    
    # Поиск по названию
    search_fields = ('name',)

@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    # Видим: Кто, Какой пакет, Остаток часов, Когда сгорит, Активен ли
    list_display = ('user', 'membership_type', 'hours_remaining', 'end_date', 'is_active')
    
    # Фильтры справа: Покажи только активные или только конкретный тип
    list_filter = ('is_active', 'membership_type', 'end_date')
    
    # Поиск: Можно найти клиента по имени или номеру телефона
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__phone')
    
    # Сортировка: Сначала те, у кого скоро сгорит абонемент
    ordering = ('end_date',)