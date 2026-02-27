from django.contrib import admin
from .models import PaymentSession


@admin.register(PaymentSession)
class PaymentSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'provider', 'status', 'description_short', 'created_at']
    list_filter = ['provider', 'status', 'created_at']
    search_fields = ['user__username', 'user__phone_number', 'provider_transaction_id', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'raw_response', 'transaction']
    ordering = ['-created_at']

    def description_short(self, obj):
        return obj.description[:60] if obj.description else '—'
    description_short.short_description = 'Описание'
