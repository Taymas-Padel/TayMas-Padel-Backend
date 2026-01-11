from django.urls import path
from .views import DirectorDashboardView

urlpatterns = [
    path('dashboard/', DirectorDashboardView.as_view(), name='director-dashboard'),
]