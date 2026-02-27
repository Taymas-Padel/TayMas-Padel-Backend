from django.urls import path
from .views import MyTransactionHistoryView, AllTransactionsView, FinanceSummaryView

urlpatterns = [
    path('history/', MyTransactionHistoryView.as_view(), name='my-transactions'),
    path('transactions/', AllTransactionsView.as_view(), name='all-transactions'),
    path('summary/', FinanceSummaryView.as_view(), name='finance-summary'),
]
