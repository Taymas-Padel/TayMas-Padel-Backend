from django.urls import path
from .views import MatchCreateView, MatchListView, LeaderboardView

urlpatterns = [
    path('matches/', MatchListView.as_view(), name='match-list'),
    path('matches/create/', MatchCreateView.as_view(), name='match-create'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
