from rest_framework import serializers
from .models import ClubSetting, ClosedDay


class ClubSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSetting
        fields = ['key', 'value', 'description']


class ClosedDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClosedDay
        fields = ['id', 'date', 'reason']