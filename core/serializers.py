from rest_framework import serializers
from .models import ClubSetting

class ClubSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSetting
        fields = ['key', 'value', 'description']