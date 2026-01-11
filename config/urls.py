from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

# Импорты для Swagger
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.conf import settings
# Настройка Swagger
schema_view = get_schema_view(
   openapi.Info(
      title="Padel Club API",
      default_version='v1',
      description="Документация для бронирования кортов",
      contact=openapi.Contact(email="admin@padel.com"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

def home(request):
    return HttpResponse("Welcome to the Booking API")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/courts/', include('courts.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
    path('', home, name='home'),

    # Маршруты для документации
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/gamification/', include('gamification.urls')),
    path('api/core/', include('core.urls')),
    path('api/memberships/', include('memberships.urls')),
    path('api/marketing/', include('marketing.urls')),
    path('api/gym/', include('gym.urls')),
    path('api/auth/', include('users.urls')),

    path('api/analytics/', include('analytics.urls')), # 👈 Добавь это
    path('api/friends/', include('friends.urls')),
]

# 👇 ДОБАВЬ ЭТОТ БЛОК В КОНЕЦ, ЕСЛИ ЕГО НЕТ
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)