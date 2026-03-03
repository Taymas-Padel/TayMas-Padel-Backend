from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf.urls.static import static
from django.conf import settings

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Padel Club API",
        default_version='v1',
        description="Документация API для бронирования кортов, CRM и мобильного приложения",
        contact=openapi.Contact(email="admin@padel.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


def home(request):
    return HttpResponse("Padel Club API v1 — /swagger/ для документации")


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Документация
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Auth (Djoser — регистрация, смена пароля и т.д.)
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),

    # Кастомный auth (SMS, CRM-вход, профиль, поиск)
    path('api/auth/', include('users.urls')),

    # Корты
    path('api/courts/', include('courts.urls')),

    # Бронирование
    path('api/bookings/', include('bookings.urls')),

    # Инвентарь / Услуги
    path('api/inventory/', include('inventory.urls')),

    # Абонементы
    path('api/memberships/', include('memberships.urls')),

    # Зал (gym, QR, персональные тренировки)
    path('api/gym/', include('gym.urls')),

    # Финансы
    path('api/finance/', include('finance.urls')),

    # Геймификация (матчи, рейтинг)
    path('api/gamification/', include('gamification.urls')),

    # Маркетинг (акции, промокоды)
    path('api/marketing/', include('marketing.urls')),

    # Новости и объявления
    path('api/news/', include('news.urls')),

    # Аналитика
    path('api/analytics/', include('analytics.urls')),

    # Друзья
    path('api/friends/', include('friends.urls')),

    # Настройки клуба
    path('api/core/', include('core.urls')),

    # Лобби (поиск партнёров)
    path('api/lobby/', include('lobby.urls')),

    # Уведомления (in-app)
    path('api/notifications/', include('notifications.urls')),

    # Платёжная система (webhook + статус сессии)
    path('api/payments/', include('payments.urls')),

    # Лиды / Воронка продаж (CRM)
    path('api/leads/', include('leads.urls')),

    path('', home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
