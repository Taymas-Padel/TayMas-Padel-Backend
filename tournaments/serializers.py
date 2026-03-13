from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Tournament, TournamentTeam, TournamentMatch
from .utils import get_round_name

User = get_user_model()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _user_brief(user):
    if not user:
        return None
    full = f'{user.first_name} {user.last_name}'.strip()
    return {
        'id': user.id,
        'name': full or user.username,
        'phone': getattr(user, 'phone_number', None),
    }


# ─────────────────────────────────────────────
# Team serializers
# ─────────────────────────────────────────────

class TournamentTeamBriefSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    player1_info = serializers.SerializerMethodField()
    player2_info = serializers.SerializerMethodField()

    class Meta:
        model = TournamentTeam
        fields = ['id', 'display_name', 'status', 'seed', 'player1_info', 'player2_info']

    def get_player1_info(self, obj):
        return _user_brief(obj.player1)

    def get_player2_info(self, obj):
        return _user_brief(obj.player2)


class TournamentTeamDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    player1_info = serializers.SerializerMethodField()
    player2_info = serializers.SerializerMethodField()
    paid_by_info = serializers.SerializerMethodField()

    class Meta:
        model = TournamentTeam
        fields = [
            'id', 'tournament', 'display_name', 'team_name',
            'player1', 'player1_info', 'player2', 'player2_info',
            'status', 'seed', 'registered_at',
            'confirmed_at', 'paid_at', 'paid_by_info', 'payment_method', 'notes',
        ]
        read_only_fields = ['id', 'registered_at', 'confirmed_at', 'paid_at', 'tournament']

    def get_player1_info(self, obj):
        return _user_brief(obj.player1)

    def get_player2_info(self, obj):
        return _user_brief(obj.player2)

    def get_paid_by_info(self, obj):
        return _user_brief(obj.paid_by)


class RegisterTeamSerializer(serializers.Serializer):
    """Регистрация команды на турнир (мобилка и CRM)."""
    player1_id = serializers.IntegerField()
    player2_id = serializers.IntegerField(required=False, allow_null=True)
    team_name  = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        tournament = self.context['tournament']
        p1_id = data['player1_id']
        p2_id = data.get('player2_id')

        if tournament.format == Tournament.Format.DOUBLES and not p2_id:
            raise serializers.ValidationError('Для парного формата нужен второй игрок.')
        if tournament.format == Tournament.Format.SINGLES and p2_id:
            raise serializers.ValidationError('Для одиночного формата второй игрок не нужен.')
        if p1_id == p2_id:
            raise serializers.ValidationError('Игрок 1 и игрок 2 не могут быть одним человеком.')

        # max teams check
        if tournament.max_teams:
            active_count = tournament.teams.exclude(
                status__in=[TournamentTeam.Status.WITHDRAWN, TournamentTeam.Status.REFUNDED]
            ).count()
            if active_count >= tournament.max_teams:
                raise serializers.ValidationError('Достигнут лимит команд в турнире.')

        # duplicate player check
        if TournamentTeam.objects.filter(tournament=tournament, player1_id=p1_id).exists():
            raise serializers.ValidationError('Игрок 1 уже зарегистрирован в этом турнире.')
        if p2_id and TournamentTeam.objects.filter(tournament=tournament, player1_id=p2_id).exists():
            raise serializers.ValidationError('Игрок 2 уже зарегистрирован как игрок 1 в этом турнире.')

        return data


class ConfirmPaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=[('CASH', 'Наличные'), ('KASPI', 'Kaspi'), ('CARD', 'Карта'), ('OTHER', 'Другое')]
    )


class UpdateTeamStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TournamentTeam.Status.choices)
    notes  = serializers.CharField(required=False, allow_blank=True)


# ─────────────────────────────────────────────
# Match serializers
# ─────────────────────────────────────────────

class TournamentMatchSerializer(serializers.ModelSerializer):
    team1_info = TournamentTeamBriefSerializer(source='team1', read_only=True)
    team2_info = TournamentTeamBriefSerializer(source='team2', read_only=True)
    winner_info = TournamentTeamBriefSerializer(source='winner', read_only=True)
    court_name  = serializers.CharField(source='court.name', read_only=True, default=None)
    round_name  = serializers.SerializerMethodField()

    class Meta:
        model = TournamentMatch
        fields = [
            'id', 'round_number', 'round_name', 'match_number',
            'team1', 'team1_info', 'team2', 'team2_info',
            'winner', 'winner_info',
            'court', 'court_name', 'scheduled_at', 'status',
            'score_team1', 'score_team2', 'notes',
            'next_match',
        ]
        read_only_fields = ['id', 'round_number', 'match_number', 'next_match', 'tournament']

    def get_round_name(self, obj):
        total = self.context.get('total_rounds', obj.tournament.matches.aggregate(
            m=__import__('django.db.models', fromlist=['Max']).Max('round_number')
        )['m'] or 1)
        return get_round_name(obj.round_number, total)


class UpdateMatchSerializer(serializers.Serializer):
    """PATCH для матча: время, корт, статус, результат."""
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    court        = serializers.PrimaryKeyRelatedField(
        queryset=__import__('courts.models', fromlist=['Court']).Court.objects.filter(is_active=True),
        required=False, allow_null=True,
    )
    status       = serializers.ChoiceField(choices=TournamentMatch.Status.choices, required=False)
    score_team1  = serializers.CharField(required=False, allow_blank=True)
    score_team2  = serializers.CharField(required=False, allow_blank=True)
    winner       = serializers.PrimaryKeyRelatedField(
        queryset=TournamentTeam.objects.all(), required=False, allow_null=True,
    )
    notes        = serializers.CharField(required=False, allow_blank=True)


# ─────────────────────────────────────────────
# Tournament serializers
# ─────────────────────────────────────────────

class TournamentListSerializer(serializers.ModelSerializer):
    teams_count      = serializers.ReadOnlyField()
    paid_teams_count = serializers.ReadOnlyField()

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'start_date', 'end_date', 'registration_deadline',
            'status', 'format', 'is_paid', 'entry_fee',
            'max_teams', 'teams_count', 'paid_teams_count', 'created_at',
        ]


class TournamentDetailSerializer(serializers.ModelSerializer):
    teams_count      = serializers.ReadOnlyField()
    paid_teams_count = serializers.ReadOnlyField()
    created_by_info  = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'registration_deadline', 'status', 'format',
            'is_paid', 'entry_fee', 'max_teams', 'prize_info',
            'teams_count', 'paid_teams_count',
            'created_by', 'created_by_info', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_created_by_info(self, obj):
        return _user_brief(obj.created_by)


class TournamentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'start_date', 'end_date',
            'registration_deadline', 'format',
            'is_paid', 'entry_fee', 'max_teams', 'prize_info',
        ]

    def validate(self, data):
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError('Дата окончания не может быть раньше начала.')
        if data.get('is_paid') and not data.get('entry_fee'):
            raise serializers.ValidationError('Укажите размер взноса для платного турнира.')
        return data


class TournamentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Tournament.Status.choices)

    def validate_status(self, value):
        tournament = self.context['tournament']
        if not tournament.can_transition_to(value):
            raise serializers.ValidationError(
                f'Нельзя перейти из статуса «{tournament.get_status_display()}» в «{dict(Tournament.Status.choices)[value]}».'
            )
        return value


# ─────────────────────────────────────────────
# Bracket serializer
# ─────────────────────────────────────────────

class BracketSerializer(serializers.Serializer):
    """Сериализует сетку по раундам."""

    def to_representation(self, tournament):
        matches = list(tournament.matches.select_related(
            'team1__player1', 'team1__player2',
            'team2__player1', 'team2__player2',
            'winner', 'court',
        ).order_by('round_number', 'match_number'))

        if not matches:
            return {'tournament_id': tournament.id, 'total_rounds': 0, 'rounds': []}

        total_rounds = max(m.round_number for m in matches)

        rounds = []
        for r in range(1, total_rounds + 1):
            r_matches = [m for m in matches if m.round_number == r]
            rounds.append({
                'round_number': r,
                'round_name': get_round_name(r, total_rounds),
                'matches': TournamentMatchSerializer(
                    r_matches, many=True,
                    context={'total_rounds': total_rounds},
                ).data,
            })

        return {
            'tournament_id': tournament.id,
            'total_rounds': total_rounds,
            'rounds': rounds,
        }
