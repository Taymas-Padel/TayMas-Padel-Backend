from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

from .models import MembershipType, UserMembership
from .serializers import MembershipTypeSerializer, UserMembershipSerializer
from finance.models import Transaction # Импортируем финансы!

# 1. Список пакетов для магазина
class MembershipTypeListView(generics.ListAPIView):
    queryset = MembershipType.objects.filter(is_active=True)
    serializer_class = MembershipTypeSerializer
    permission_classes = [permissions.AllowAny]

# 2. Покупка пакета
class BuyMembershipView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Находим пакет
        mem_type = get_object_or_404(MembershipType, pk=pk)
        user = request.user

        # Рассчитываем дату окончания
        end_date = timezone.now() + timedelta(days=mem_type.days_valid)

        # 1. Создаем запись о владении (начисляем часы)
        UserMembership.objects.create(
            user=user,
            membership_type=mem_type,
            end_date=end_date,
            hours_remaining=mem_type.total_hours,
            is_active=True
        )

        # 2. Записываем в Финансы (что мы заработали денег)
        Transaction.objects.create(
            user=user,
            amount=mem_type.price,
            transaction_type='PAYMENT', # Или создать тип 'MEMBERSHIP'
            description=f"Покупка абонемента: {mem_type.name}"
        )

        return Response({"status": "Абонемент успешно куплен!"}, status=status.HTTP_201_CREATED)