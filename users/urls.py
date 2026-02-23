from django.urls import path
from .views import (
    SendCodeView,
    MobileLoginView,
    CRMLoginView,
    UserSearchView,
    receptionist_search_view,
    receptionist_action_view,
    receptionist_user_detail_view,
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

    # === Публичный поиск (приложение — друзья) ===
    path('search/', UserSearchView.as_view(), name='user-search'),

    # УБРАЛИ: jwt/refresh/ — он уже есть в djoser.urls.jwt, дублирование не нужно
]