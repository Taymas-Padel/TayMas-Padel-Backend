from django.urls import path
from .views import PaymentWebhookView, PaymentStatusView

urlpatterns = [
    # Webhook от провайдера (Kaspi, CloudPayments и т.д.)
    path('webhook/<str:provider>/', PaymentWebhookView.as_view(), name='payment-webhook'),
    # Статус сессии (для polling)
    path('session/<str:session_id>/status/', PaymentStatusView.as_view(), name='payment-status'),
]
