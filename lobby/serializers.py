from rest_framework import serializers
from .models import Lobby, LobbyParticipant, LobbyParticipantExtra, LobbyTimeProposal
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class LobbyParticipantExtraSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = LobbyParticipantExtra
        fields = ['id', 'service', 'service_name', 'quantity', 'price_at_moment', 'subtotal']

    def get_subtotal(self, obj):
        return str(obj.subtotal())


class LobbyParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    rating_elo = serializers.IntegerField(source='user.rating_elo', read_only=True)
    extras = LobbyParticipantExtraSerializer(many=True, read_only=True)
    extras_total = serializers.SerializerMethodField()
    total_to_pay = serializers.SerializerMethodField()

    class Meta:
        model = LobbyParticipant
        fields = [
            'id', 'user', 'user_name', 'rating_elo',
            'team', 'court_share', 'membership_used',
            'extras', 'extras_total', 'share_amount', 'total_to_pay',
            'is_paid', 'joined_at',
        ]

    def get_user_name(self, obj):
        full = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full or obj.user.username

    def get_extras_total(self, obj):
        return str(obj.extras_total())

    def get_total_to_pay(self, obj):
        return str((obj.share_amount or Decimal('0')))


class LobbyTimeProposalSerializer(serializers.ModelSerializer):
    proposed_by_name = serializers.SerializerMethodField()
    court_name = serializers.CharField(source='court.name', read_only=True)
    court_price = serializers.DecimalField(
        source='court.price_per_hour', max_digits=10, decimal_places=2, read_only=True
    )
    votes_count = serializers.SerializerMethodField()
    i_voted = serializers.SerializerMethodField()
    estimated_share = serializers.SerializerMethodField()

    class Meta:
        model = LobbyTimeProposal
        fields = [
            'id', 'lobby', 'proposed_by', 'proposed_by_name',
            'court', 'court_name', 'court_price',
            'scheduled_time', 'duration_minutes',
            'votes_count', 'i_voted', 'is_accepted',
            'estimated_share', 'created_at',
        ]
        read_only_fields = ['proposed_by', 'is_accepted', 'created_at']

    def get_proposed_by_name(self, obj):
        full = f"{obj.proposed_by.first_name} {obj.proposed_by.last_name}".strip()
        return full or obj.proposed_by.username

    def get_votes_count(self, obj):
        return obj.votes.count()

    def get_i_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.votes.filter(pk=request.user.pk).exists()
        return False

    def get_estimated_share(self, obj):
        """Предварительная доля корта (+ тренер при наличии) на одного игрока."""
        n = obj.lobby.current_players_count() or obj.lobby.max_players()
        if not n:
            return None
        hours = Decimal(str(obj.duration_minutes / 60))
        court_total = Decimal(str(obj.court.price_per_hour)) * hours
        coach_total = Decimal('0')
        if obj.lobby.coach and getattr(obj.lobby.coach, 'price_per_hour', None) is not None:
            coach_total = Decimal(str(obj.lobby.coach.price_per_hour)) * hours
        total = court_total + coach_total
        share = (total / n).quantize(Decimal('0.01'))
        return str(share)


class LobbySerializer(serializers.ModelSerializer):
    participants = LobbyParticipantSerializer(many=True, read_only=True)
    proposals = LobbyTimeProposalSerializer(many=True, read_only=True)
    creator_name = serializers.SerializerMethodField()
    players_count = serializers.SerializerMethodField()
    max_players = serializers.SerializerMethodField()
    court_name = serializers.CharField(source='court.name', read_only=True, allow_null=True)
    court_price = serializers.DecimalField(
        source='court.price_per_hour', max_digits=10, decimal_places=2,
        read_only=True, allow_null=True
    )
    booking_id = serializers.IntegerField(source='booking.id', read_only=True, allow_null=True)
    booking_status = serializers.CharField(source='booking.status', read_only=True, allow_null=True)
    booking_price = serializers.DecimalField(
        source='booking.price', max_digits=10, decimal_places=2,
        read_only=True, allow_null=True
    )
    paid_count = serializers.SerializerMethodField()
    estimated_share = serializers.SerializerMethodField()
    elo_label = serializers.SerializerMethodField()
    coach_name = serializers.SerializerMethodField()

    class Meta:
        model = Lobby
        fields = [
            'id', 'creator', 'creator_name', 'title', 'game_format',
            'elo_min', 'elo_max', 'elo_label',
            'status', 'court', 'court_name', 'court_price',
            'scheduled_time', 'duration_minutes', 'comment',
            'coach', 'coach_name',
            'players_count', 'max_players', 'estimated_share',
            'booking_id', 'booking_status', 'booking_price', 'paid_count',
            'participants', 'proposals', 'created_at',
        ]
        read_only_fields = ['creator', 'status', 'booking', 'court', 'scheduled_time',
                            'duration_minutes', 'created_at']

    def get_coach_name(self, obj):
        if not obj.coach:
            return None
        full = f"{obj.coach.first_name} {obj.coach.last_name}".strip()
        return full or obj.coach.username

    def get_creator_name(self, obj):
        full = f"{obj.creator.first_name} {obj.creator.last_name}".strip()
        return full or obj.creator.username

    def get_players_count(self, obj):
        return obj.current_players_count()

    def get_max_players(self, obj):
        return obj.max_players()

    def get_paid_count(self, obj):
        return obj.participants.filter(is_paid=True).count()

    def get_elo_label(self, obj):
        """Человекочитаемый ELO диапазон, напр. '800–1200'."""
        if obj.elo_min == 0 and obj.elo_max == 9999:
            return 'Любой уровень'
        return f"{obj.elo_min}–{obj.elo_max} ELO"

    def get_estimated_share(self, obj):
        """Предварительная стоимость доли корта + тренер (после согласования)."""
        if not obj.court or not obj.duration_minutes:
            return None
        n = obj.current_players_count() or obj.max_players()
        if not n:
            return None
        hours = Decimal(str(obj.duration_minutes / 60))
        court_total = Decimal(str(obj.court.price_per_hour)) * hours
        coach_total = Decimal('0')
        if obj.coach and getattr(obj.coach, 'price_per_hour', None) is not None:
            coach_total = Decimal(str(obj.coach.price_per_hour)) * hours
        total = court_total + coach_total
        share = (total / n).quantize(Decimal('0.01'))
        return str(share)


class LobbyPatchSerializer(serializers.ModelSerializer):
    """Только coach и comment — для PATCH создателем до создания брони."""
    class Meta:
        model = Lobby
        fields = ['coach', 'comment']
