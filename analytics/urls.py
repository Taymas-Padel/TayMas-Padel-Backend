from django.urls import path
from .views import DirectorDashboardView, ReceptionDashboardView

urlpatterns = [
    path('dashboard/', DirectorDashboardView.as_view(), name='director-dashboard'),
    path('reception/', ReceptionDashboardView.as_view(), name='reception-dashboard'),
]
