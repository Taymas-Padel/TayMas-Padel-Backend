from django.urls import path
from .views import (
    SendCodeView,
    MobileLoginView,
    CRMLoginView,
    UserSearchView,
    receptionist_search_view,
    receptionist_action_view,
    receptionist_user_detail_view,
    ClientListView,
    CoachesListView,
    UpdateFCMTokenView,
    MyStatsView,
    HomeDashboardView,
    PublicUserProfileView,
    AccountDeleteView,
    MyLeagueView,
)

urlpatterns = [
    # === Мобильное приложение — вход по SMS ===
    path('mobile/send-code/', SendCodeView.as_view(), name='mobile-send-code'),
    path('mobile/login/', MobileLoginView.as_view(), name='mobile-login'),

    # === CRM — вход по паролю (ресепшн / админ) ===
    path('crm/login/', CRMLoginView.as_view(), name='crm-login'),

    # === Ресепшн — работа с клиентами ===
    path('reception/search/', receptionist_search_view, name='reception-search'),
    path('reception/user/<int:pk>/', receptionist_user_detail_view, name='reception-user-detail'),
    path('reception/user/<int:pk>/action/', receptionist_action_view, name='reception-action'),

    # === CRM — список клиентов ===
    path('clients/', ClientListView.as_view(), name='client-list'),

    # === Список тренеров (для брони в приложении и CRM) ===
    path('coaches/', CoachesListView.as_view(), name='coaches-list'),
    path('me/fcm/', UpdateFCMTokenView.as_view(), name='update-fcm-token'),
    path('me/league/', MyLeagueView.as_view(), name='my-league'),
    path('me/delete/', AccountDeleteView.as_view(), name='account-delete'),

    # === Публичный поиск (приложение — друзья) ===
    path('search/', UserSearchView.as_view(), name='user-search'),

    # === Публичный профиль пользователя ===
    path('users/<int:pk>/profile/', PublicUserProfileView.as_view(), name='public-user-profile'),

    # === Мобилка — персональный кабинет ===
    path('me/stats/', MyStatsView.as_view(), name='my-stats'),
    path('home/', HomeDashboardView.as_view(), name='home-dashboard'),
]
