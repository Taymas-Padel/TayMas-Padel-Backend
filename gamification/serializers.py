from rest_framework import serializers
from .models import Match
from django.contrib.auth import get_user_model

User = get_user_model()


class MatchSerializer(serializers.ModelSerializer):
    team_a_names = serializers.SerializerMethodField()
    team_b_names = serializers.SerializerMethodField()
    judge_name = serializers.SerializerMethodField()
    date_formatted = serializers.SerializerMethodField()

    my_elo_change = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id', 'team_a', 'team_b', 'score', 'winner_team', 'court',
            'team_a_names', 'team_b_names', 'judge_name', 'date', 'date_formatted',
            'is_rated', 'elo_changes', 'my_elo_change',
        ]
        read_only_fields = ['id', 'date', 'judge', 'is_rated', 'elo_changes']

    def get_my_elo_change(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return obj.elo_changes.get(str(request.user.id))

    def get_team_a_names(self, obj):
        return [
            {"id": u.id, "name": f"{u.first_name} {u.last_name}".strip() or u.username}
            for u in obj.team_a.all()
        ]

    def get_team_b_names(self, obj):
        return [
            {"id": u.id, "name": f"{u.first_name} {u.last_name}".strip() or u.username}
            for u in obj.team_b.all()
        ]

    def get_judge_name(self, obj):
        if not obj.judge:
            return None
        return f"{obj.judge.first_name} {obj.judge.last_name}".strip() or obj.judge.username

    def get_date_formatted(self, obj):
        return obj.date.strftime('%d.%m.%Y %H:%M')

    def validate(self, data):
        team_a = data.get('team_a', [])
        team_b = data.get('team_b', [])
        if set(team_a) & set(team_b):
            raise serializers.ValidationError("Один игрок не может быть в обеих командах.")
        return data


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    matches_played = serializers.SerializerMethodField()
    matches_won = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar', 'rating_elo', 'matches_played', 'matches_won']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_matches_played(self, obj):
        from django.db.models import Q
        return Match.objects.filter(Q(team_a=obj) | Q(team_b=obj)).distinct().count()

    def get_matches_won(self, obj):
        from django.db.models import Q
        return Match.objects.filter(
            Q(team_a=obj, winner_team='A') | Q(team_b=obj, winner_team='B')
        ).distinct().count()
