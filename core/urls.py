from django.urls import path
from .views import ClubSettingListView, ClubSettingDetailView, ClosedDaysListView

urlpatterns = [
    path('settings/', ClubSettingListView.as_view(), name='club-settings'),
    path('settings/<str:key>/', ClubSettingDetailView.as_view(), name='club-setting-detail'),
    path('closed-days/', ClosedDaysListView.as_view(), name='closed-days'),
]