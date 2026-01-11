from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 
            'amount', 
            'transaction_type', 
            'description', 
            'created_at', 
            'created_at_formatted',
            # Детализация
            'amount_court',
            'amount_coach',
            'amount_services',
            'amount_discount' # <--- ДОБАВИЛИ СЮДА
        ]

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')