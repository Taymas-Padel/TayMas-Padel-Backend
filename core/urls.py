from django.urls import path
from .views import ClubSettingListView

urlpatterns = [
    path('settings/', ClubSettingListView.as_view(), name='club-settings'),
]