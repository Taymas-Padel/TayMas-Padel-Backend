from rest_framework import serializers
from .models import MembershipType, UserMembership
from finance.models import Transaction


class MembershipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipType
        fields = '__all__'


class UserMembershipSerializer(serializers.ModelSerializer):
    membership_type_name = serializers.CharField(source='membership_type.name', read_only=True)
    type_name = serializers.CharField(source='membership_type.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    visits_remaining = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    is_paid = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    class Meta:
        model = UserMembership
        fields = [
            'id',
            'user',
            'user_name',
            'membership_type_name',
            'type_name',
            'start_date',
            'end_date',
            'hours_remaining',
            'visits_remaining',
            'is_active',
            'is_frozen',
            'freeze_start_date',
            'created_at',
            'is_paid',
            'payment_amount',
        ]

    def get_user_name(self, obj):
        u = obj.user
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.phone_number or u.username

    def get_visits_remaining(self, obj):
        return getattr(obj, 'visits_remaining', None)

    def _get_payment_transaction(self, obj):
        if not getattr(obj, '_payment_txn_cached', None) and not hasattr(obj, '_payment_txn'):
            obj._payment_txn = Transaction.objects.filter(
                user_membership=obj,
                transaction_type=Transaction.TransactionType.MEMBERSHIP_PURCHASE,
            ).first()
            obj._payment_txn_cached = True
        return getattr(obj, '_payment_txn', None)

    def get_is_paid(self, obj):
        return self._get_payment_transaction(obj) is not None

    def get_payment_amount(self, obj):
        t = self._get_payment_transaction(obj)
        return str(t.amount) if t else '0'





