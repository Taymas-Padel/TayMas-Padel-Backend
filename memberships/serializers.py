from rest_framework import serializers
from .models import MembershipType, UserMembership

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
        ]

    def get_user_name(self, obj):
        u = obj.user
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.phone_number or u.username

    def get_visits_remaining(self, obj):
        return getattr(obj, 'visits_remaining', None)





