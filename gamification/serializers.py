from rest_framework import serializers
from .models import Match
from django.contrib.auth import get_user_model

User = get_user_model()

class MatchSerializer(serializers.ModelSerializer):
    # Показываем имена игроков вместо просто ID при чтении
    team_a_names = serializers.SerializerMethodField()
    team_b_names = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = ['id', 'team_a', 'team_b', 'score', 'winner_team', 'court', 'team_a_names', 'team_b_names', 'date']
        read_only_fields = ['id', 'date', 'judge', 'is_rated']

    def get_team_a_names(self, obj):
        return [user.username for user in obj.team_a.all()]

    def get_team_b_names(self, obj):
        return [user.username for user in obj.team_b.all()]

    def validate(self, data):
        # Проверка: нельзя играть против самого себя
        team_a = data.get('team_a', [])
        team_b = data.get('team_b', [])
        
        # Пересечение множеств (есть ли общие игроки)
        if set(team_a) & set(team_b):
            raise serializers.ValidationError("Один и тот же игрок не может быть в обеих командах.")
            
        return data