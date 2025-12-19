from rest_framework import serializers
from .models import MembershipType, UserMembership

class MembershipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipType
        fields = '__all__'

class UserMembershipSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='membership_type.name', read_only=True)
    
    class Meta:
        model = UserMembership
        fields = ['id', 'type_name', 'start_date', 'end_date', 'hours_remaining', 'is_active']