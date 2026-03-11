from rest_framework import serializers
from .models import MembershipType, UserMembership
from finance.models import Transaction


class MembershipTypeSerializer(serializers.ModelSerializer):
    service_type_display = serializers.CharField(
        source='get_service_type_display', read_only=True,
    )

    class Meta:
        model = MembershipType
        fields = [
            'id',
            'name',
            'description',
            'service_type',
            'service_type_display',
            'price',
            'days_valid',
            'total_hours',
            'total_visits',
            'priority_time_start',
            'priority_time_end',
            'prime_time_surcharge',
            'min_participants',
            'max_participants',
            'includes_coach',
            'court_type_restriction',
            'discount_on_court',
            'is_active',
        ]


class UserMembershipSerializer(serializers.ModelSerializer):
    membership_type_name = serializers.CharField(source='membership_type.name', read_only=True)
    type_name = serializers.CharField(source='membership_type.name', read_only=True)
    service_type = serializers.CharField(source='membership_type.service_type', read_only=True)
    service_type_display = serializers.CharField(
        source='membership_type.get_service_type_display', read_only=True,
    )
    user_name = serializers.SerializerMethodField()
    visits_remaining = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(source='start_date', read_only=True)
    is_paid = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    # Новые поля из MembershipType для удобства фронта
    priority_time_start = serializers.TimeField(
        source='membership_type.priority_time_start', read_only=True,
    )
    priority_time_end = serializers.TimeField(
        source='membership_type.priority_time_end', read_only=True,
    )
    prime_time_surcharge = serializers.DecimalField(
        source='membership_type.prime_time_surcharge',
        max_digits=10, decimal_places=2, read_only=True,
    )
    includes_coach = serializers.BooleanField(
        source='membership_type.includes_coach', read_only=True,
    )
    min_participants = serializers.IntegerField(
        source='membership_type.min_participants', read_only=True,
    )
    max_participants = serializers.IntegerField(
        source='membership_type.max_participants', read_only=True,
    )

    class Meta:
        model = UserMembership
        fields = [
            'id',
            'user',
            'user_name',
            'membership_type',
            'membership_type_name',
            'type_name',
            'service_type',
            'service_type_display',
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
            'priority_time_start',
            'priority_time_end',
            'prime_time_surcharge',
            'includes_coach',
            'min_participants',
            'max_participants',
        ]

    def get_user_name(self, obj):
        u = obj.user
        full = f"{u.first_name} {u.last_name}".strip()
        return full or getattr(u, 'phone_number', None) or u.username

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
