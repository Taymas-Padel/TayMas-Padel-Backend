from django.urls import path
from .views import CourtListAPIView

urlpatterns = [
    path('', CourtListAPIView.as_view(), name='court-list'),
]