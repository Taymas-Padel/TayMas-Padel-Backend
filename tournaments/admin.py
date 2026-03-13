from django.contrib import admin
from .models import Tournament, TournamentTeam, TournamentMatch


class TournamentTeamInline(admin.TabularInline):
    model = TournamentTeam
    extra = 0
    fields = ('player1', 'player2', 'team_name', 'status', 'seed', 'paid_at', 'payment_method')
    readonly_fields = ('paid_at',)
    show_change_link = True


class TournamentMatchInline(admin.TabularInline):
    model = TournamentMatch
    extra = 0
    fields = ('round_number', 'match_number', 'team1', 'team2', 'winner', 'scheduled_at', 'court', 'status', 'score_team1', 'score_team2')
    readonly_fields = ('round_number', 'match_number')
    show_change_link = True


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'format', 'status', 'start_date', 'end_date', 'is_paid', 'entry_fee', 'teams_count')
    list_filter = ('status', 'format', 'is_paid')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'teams_count', 'paid_teams_count')
    inlines = [TournamentTeamInline, TournamentMatchInline]

    def teams_count(self, obj):
        return obj.teams_count
    teams_count.short_description = 'Команд'


@admin.register(TournamentTeam)
class TournamentTeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'tournament', 'display_name', 'status', 'seed', 'paid_at', 'payment_method')
    list_filter = ('status', 'tournament')
    search_fields = ('player1__username', 'player1__phone_number', 'team_name')
    readonly_fields = ('registered_at', 'confirmed_at', 'paid_at')

    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = 'Команда'


@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'tournament', 'round_number', 'match_number', 'team1', 'team2', 'winner', 'scheduled_at', 'court', 'status')
    list_filter = ('status', 'tournament', 'round_number')
    search_fields = ('tournament__name',)
    autocomplete_fields = ('court',)
