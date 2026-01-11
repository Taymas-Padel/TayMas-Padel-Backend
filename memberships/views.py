from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework import viewsets

from .models import MembershipType, UserMembership
from .serializers import MembershipTypeSerializer, UserMembershipSerializer
from finance.models import Transaction # Импортируем нашу крутую модель

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

        # 1. Создаем абонемент и СОХРАНЯЕМ В ПЕРЕМЕННУЮ (чтобы получить ID)
        user_membership = UserMembership.objects.create(
            user=user,
            membership_type=mem_type,
            end_date=end_date,
            hours_remaining=mem_type.total_hours,
            visits_remaining=mem_type.total_visits, # Не забудь это поле, если оно есть в модели
            is_active=True
        )

        # 2. 🔥 ЗАПИСЫВАЕМ ТРАНЗАКЦИЮ (С НОВОЙ ЛОГИКОЙ)
        Transaction.objects.create(
            user=user,
            
            # Деньги
            amount=mem_type.price,
            
            # Тип операции (Берем из ENUM в модели)
            transaction_type=Transaction.TransactionType.MEMBERSHIP_PURCHASE,
            
            # Способ оплаты (Пока ставим Kaspi по умолчанию, позже сделаешь выбор)
            payment_method=Transaction.PaymentMethod.KASPI,
            
            # 👇 САМОЕ ГЛАВНОЕ: ССЫЛКА НА АБОНЕМЕНТ
            user_membership=user_membership, 
            
            description=f"Покупка абонемента: {mem_type.name}"
        )

        return Response({"status": "Абонемент успешно куплен!"}, status=status.HTTP_201_CREATED)

# ViewSet для управления абонементами
class UserMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр абонементов и управление ими (Заморозка)
    """
    serializer_class = UserMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 1. Fix for Swagger
        if getattr(self, 'swagger_fake_view', False):
            return UserMembership.objects.none()
        # 2. Fix for Anonymous
        if not self.request.user.is_authenticated:
            return UserMembership.objects.none()
        # 3. Real Logic
        return UserMembership.objects.filter(user=self.request.user)

    # 1. ЗАМОРОЗКА ❄️
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        membership = self.get_object()
        
        if membership.is_frozen:
            return Response({"error": "Абонемент уже заморожен"}, status=400)
        
        if not membership.is_active:
             return Response({"error": "Нельзя заморозить неактивный абонемент"}, status=400)

        membership.is_frozen = True
        membership.freeze_start_date = timezone.now()
        membership.save()
        
        return Response({"status": "Абонемент заморожен. Срок действия приостановлен."})

    # 2. РАЗМОРОЗКА 🔥
    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        membership = self.get_object()
        
        if not membership.is_frozen:
            return Response({"error": "Абонемент не был заморожен"}, status=400)

        now = timezone.now()
        frozen_duration = now - membership.freeze_start_date
        
        membership.end_date += frozen_duration
        membership.is_frozen = False
        membership.freeze_start_date = None
        membership.save()
        
        return Response({
            "status": "Абонемент разморожен.", 
            "new_end_date": membership.end_date.strftime('%Y-%m-%d')
        })
    
    # 3. ИСТОРИЯ СПИСАНИЙ 📜
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """История транзакций по этому абонементу"""
        membership = self.get_object()
        
        from finance.serializers import TransactionSerializer 

        # 🔥 ТЕПЕРЬ МЫ ИЩЕМ ПО ID (Это работает мгновенно и точно)
        # Мы ищем все транзакции, которые ссылаются на этот абонемент
        transactions = Transaction.objects.filter(
            user_membership=membership 
        ).order_by('-created_at')

        # Если список пуст (например, абонемент старый), можно попробовать найти по дате,
        # но в новой системе связь будет работать железно.
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)