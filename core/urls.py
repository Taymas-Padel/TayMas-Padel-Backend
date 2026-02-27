from django.urls import path
from .views import ClubSettingListView, ClosedDaysListView

urlpatterns = [
    path('settings/', ClubSettingListView.as_view(), name='club-settings'),
    path('closed-days/', ClosedDaysListView.as_view(), name='closed-days'),
]