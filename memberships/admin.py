from django.contrib import admin
from .models import MembershipType, UserMembership


@admin.register(MembershipType)
class MembershipTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'service_type', 'price', 'total_hours',
        'days_valid', 'priority_time_start', 'priority_time_end',
        'prime_time_surcharge', 'includes_coach', 'max_quantity',
        'is_active',
    )
    list_editable = ('price', 'is_active')
    list_filter = ('service_type', 'is_active', 'includes_coach')
    search_fields = ('name',)

    fieldsets = (
        ('Основное', {
            'fields': ('name', 'description', 'service_type', 'price', 'days_valid', 'is_active'),
        }),
        ('Лимиты', {
            'fields': ('total_hours', 'total_visits', 'max_quantity'),
        }),
        ('Приоритетное время / Прайм-тайм', {
            'fields': (
                'priority_time_start', 'priority_time_end', 'prime_time_surcharge',
            ),
            'description': (
                'Если указаны — часы пакета расходуются без доплаты '
                'только в приоритетное окно. За прайм-тайм — доплата ₸/час.'
            ),
        }),
        ('Участники и тренер', {
            'fields': ('min_participants', 'max_participants', 'includes_coach'),
        }),
        ('Ограничения', {
            'fields': ('court_type_restriction', 'discount_on_court'),
        }),
    )


@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'membership_type', 'hours_remaining',
        'visits_remaining', 'end_date', 'is_active', 'is_frozen',
    )
    list_filter = ('is_active', 'is_frozen', 'membership_type__service_type', 'membership_type')
    search_fields = (
        'user__username', 'user__first_name',
        'user__last_name', 'user__phone_number',
    )
    ordering = ('end_date',)
    raw_id_fields = ('user',)
