from django.urls import path
from .views import (
    TournamentListView,
    TournamentDetailView,
    TournamentCreateView,
    TournamentManageListView,
    TournamentUpdateView,
    TournamentStatusView,
    TournamentTeamsView,
    TournamentTeamDetailView,
    ConfirmTeamPaymentView,
    RefundTeamPaymentView,
    TournamentBracketView,
    GenerateBracketView,
    TournamentMatchesView,
    TournamentMatchDetailView,
    MyTournamentMatchesView,
    TournamentReportView,
)

urlpatterns = [
    # ── Публичные / для мобилки ──────────────────────────────────
    path('', TournamentListView.as_view(), name='tournament-list'),
    path('<int:pk>/', TournamentDetailView.as_view(), name='tournament-detail'),
    path('<int:pk>/teams/', TournamentTeamsView.as_view(), name='tournament-teams'),
    path('<int:tid>/teams/<int:team_id>/', TournamentTeamDetailView.as_view(), name='tournament-team-detail'),
    path('<int:pk>/bracket/', TournamentBracketView.as_view(), name='tournament-bracket'),
    path('<int:pk>/matches/', TournamentMatchesView.as_view(), name='tournament-matches'),
    path('<int:tid>/matches/<int:match_id>/', TournamentMatchDetailView.as_view(), name='tournament-match-detail'),
    path('<int:pk>/my-matches/', MyTournamentMatchesView.as_view(), name='tournament-my-matches'),

    # ── CRM / Manage (ADMIN / RECEPTIONIST) ─────────────────────
    path('manage/', TournamentManageListView.as_view(), name='tournament-manage-list'),
    path('manage/create/', TournamentCreateView.as_view(), name='tournament-create'),
    path('manage/<int:pk>/', TournamentUpdateView.as_view(), name='tournament-update'),
    path('manage/<int:pk>/status/', TournamentStatusView.as_view(), name='tournament-status'),
    path('manage/<int:pk>/generate-bracket/', GenerateBracketView.as_view(), name='tournament-generate-bracket'),
    path('manage/<int:pk>/report/', TournamentReportView.as_view(), name='tournament-report'),

    # ── Команды (управление оплатой) ────────────────────────────
    path('manage/<int:tid>/teams/<int:team_id>/confirm-payment/',
         ConfirmTeamPaymentView.as_view(), name='team-confirm-payment'),
    path('manage/<int:tid>/teams/<int:team_id>/refund/',
         RefundTeamPaymentView.as_view(), name='team-refund'),

    # ── Матчи (управление) ──────────────────────────────────────
    path('manage/<int:tid>/matches/<int:match_id>/',
         TournamentMatchDetailView.as_view(), name='tournament-match-manage'),
]
