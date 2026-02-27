"""
Webhook endpoint — принимает колбэки от платёжных провайдеров.
При подключении реального провайдера — прописать его URL в личном кабинете.

URL: POST /api/payments/webhook/<provider>/
"""
import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from .service import PaymentService

logger = logging.getLogger(__name__)


class PaymentWebhookView(APIView):
    """
    POST /api/payments/webhook/<provider>/
    Принимает webhook от платёжного провайдера.
    Аутентификация НЕ требуется (провайдер не передаёт JWT).
    Верификация — через подпись в заголовке (реализовать в handle_webhook).
    """
    permission_classes = [permissions.AllowAny]
    # Отключаем CSRF для webhook (провайдер — внешний сервис)
    authentication_classes = []

    def post(self, request, provider: str):
        try:
            raw_data = request.data if isinstance(request.data, dict) else json.loads(request.body)
        except Exception:
            raw_data = {}

        logger.info(f"[Webhook] Получен от провайдера '{provider}': {raw_data}")

        success = PaymentService.handle_webhook(
            provider_name=provider.lower(),
            raw_data=raw_data,
        )

        if success:
            return Response({"status": "ok"})
        else:
            # Всегда возвращаем 200 провайдеру (иначе будет повторная отправка)
            return Response({"status": "ignored"})


class PaymentStatusView(APIView):
    """
    GET /api/payments/session/<session_id>/status/
    Клиент может опросить статус своей платёжной сессии.
    Используется когда провайдер требует polling вместо webhook.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id: str):
        from .models import PaymentSession
        from django.shortcuts import get_object_or_404

        session = get_object_or_404(PaymentSession, id=session_id, user=request.user)
        return Response({
            "session_id": str(session.id),
            "status": session.status,
            "amount": str(session.amount),
            "provider": session.provider,
            "payment_url": session.payment_url or None,
            "transaction_id": session.transaction_id,
            "created_at": session.created_at,
        })
