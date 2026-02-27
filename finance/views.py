from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.utils import timezone

from .models import Transaction
from .serializers import TransactionSerializer
from users.permissions import IsReceptionist, IsAdminRole


class MyTransactionHistoryView(generics.ListAPIView):
    """
    GET /api/finance/history/
    История транзакций текущего пользователя (клиент видит только свои).
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class AllTransactionsView(generics.ListAPIView):
    """
    GET /api/finance/transactions/?date=&type=&method=&user_id=
    Все транзакции (только для ресепшн/админа). Поддерживает фильтры.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        qs = Transaction.objects.select_related('user', 'booking').all()

        date_str = self.request.query_params.get('date')
        if date_str:
            from datetime import datetime
            from django.utils.timezone import make_aware
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
                qs = qs.filter(created_at__date=d)
            except ValueError:
                pass

        t_type = self.request.query_params.get('type')
        if t_type:
            qs = qs.filter(transaction_type=t_type.upper())

        method = self.request.query_params.get('method')
        if method:
            qs = qs.filter(payment_method=method.upper())

        user_id = self.request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs.order_by('-created_at')


class FinanceSummaryView(APIView):
    """
    GET /api/finance/summary/?period=today|month|all
    Итоговая сводка по финансам для ресепшн (за день/месяц/всё время).
    """
    permission_classes = [IsReceptionist]

    def get(self, request):
        period = request.query_params.get('period', 'today')
        now = timezone.now()

        if period == 'today':
            qs = Transaction.objects.filter(created_at__date=now.date())
        elif period == 'month':
            qs = Transaction.objects.filter(
                created_at__year=now.year,
                created_at__month=now.month,
            )
        else:
            qs = Transaction.objects.all()

        total = qs.aggregate(t=Sum('amount'))['t'] or 0
        by_method = {}
        for m_code, m_label in Transaction.PaymentMethod.choices:
            val = qs.filter(payment_method=m_code).aggregate(t=Sum('amount'))['t'] or 0
            if val != 0:
                by_method[m_label] = float(val)

        by_type = {}
        for t_code, t_label in Transaction.TransactionType.choices:
            val = qs.filter(transaction_type=t_code).aggregate(t=Sum('amount'))['t'] or 0
            if val != 0:
                by_type[t_label] = float(val)

        return Response({
            "period": period,
            "total": float(total),
            "by_payment_method": by_method,
            "by_type": by_type,
        })
