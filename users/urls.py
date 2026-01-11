from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SendCodeView, 
    MobileLoginView, 
    UserSearchView,
    # 👇 Не забудь импортировать новые вьюхи!
    search_user_view, 
    manager_user_action_view
)

urlpatterns = [
    path('mobile/send-code/', SendCodeView.as_view(), name='mobile-send-code'),
    path('mobile/login/', MobileLoginView.as_view(), name='mobile-login'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 👇 НОВЫЕ ПУТИ ДЛЯ МЕНЕДЖЕРА
    path('manager/search/', search_user_view, name='manager-search'),
    path('manager/user/<int:pk>/action/', manager_user_action_view, name='manager-action'),
    path('search/', UserSearchView.as_view(), name='user-search'),
]