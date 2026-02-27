from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    transaction_type_label = serializers.SerializerMethodField()
    payment_method_label = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id',
            'amount',
            'transaction_type',
            'transaction_type_label',
            'payment_method',
            'payment_method_label',
            'description',
            'created_at',
            'created_at_formatted',
            'amount_court',
            'amount_coach',
            'amount_services',
            'amount_discount',
            'booking',
            'user_membership',
        ]

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

    def get_transaction_type_label(self, obj):
        return obj.get_transaction_type_display()

    def get_payment_method_label(self, obj):
        return obj.get_payment_method_display()
