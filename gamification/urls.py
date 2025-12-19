from django.urls import path
from .views import MatchCreateView

urlpatterns = [
    path('matches/create/', MatchCreateView.as_view(), name='match-create'),
]