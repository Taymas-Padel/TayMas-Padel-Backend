from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'user', 'amount', 'transaction_type', 'booking')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)