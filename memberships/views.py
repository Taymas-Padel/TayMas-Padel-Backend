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
from finance.models import Transaction
from users.permissions import IsReceptionist

# 1. Список пакетов для магазина (публичный)
class MembershipTypeListView(generics.ListAPIView):
    queryset = MembershipType.objects.filter(is_active=True)
    serializer_class = MembershipTypeSerializer
    permission_classes = [permissions.AllowAny]


# 1b. Управление типами абонементов (ADMIN) — как в админке
class MembershipTypeManageView(generics.ListCreateAPIView):
    """GET/POST /api/memberships/types/manage/ — все типы + создание (ADMIN)."""
    queryset = MembershipType.objects.all().order_by('service_type', 'name')
    serializer_class = MembershipTypeSerializer
    permission_classes = [IsReceptionist]  # ресепшн и админ могут создавать типы


class MembershipTypeManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/memberships/types/manage/<id>/ (ADMIN)."""
    queryset = MembershipType.objects.all()
    serializer_class = MembershipTypeSerializer
    permission_classes = [IsReceptionist]

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


class ReceptionBuyMembershipView(APIView):
    """
    POST /api/memberships/reception/buy/
    Ресепшн/Админ выдаёт абонемент клиенту вручную.
    Body: { client_id, membership_type_id, payment_method }
    """
    permission_classes = [IsReceptionist]

    def post(self, request):
        from users.models import User
        client_id = request.data.get('client_id')
        type_id = request.data.get('membership_type_id')
        payment_method = request.data.get('payment_method', Transaction.PaymentMethod.CASH)

        if not client_id or not type_id:
            return Response({'error': 'Укажите client_id и membership_type_id'}, status=400)

        user = get_object_or_404(User, pk=client_id)
        mem_type = get_object_or_404(MembershipType, pk=type_id, is_active=True)

        valid_methods = [c[0] for c in Transaction.PaymentMethod.choices]
        if payment_method not in valid_methods:
            payment_method = Transaction.PaymentMethod.CASH

        end_date = timezone.now() + timedelta(days=mem_type.days_valid)

        user_membership = UserMembership.objects.create(
            user=user,
            membership_type=mem_type,
            end_date=end_date,
            hours_remaining=mem_type.total_hours,
            visits_remaining=mem_type.total_visits,
            is_active=True,
        )

        Transaction.objects.create(
            user=user,
            amount=mem_type.price,
            transaction_type=Transaction.TransactionType.MEMBERSHIP_PURCHASE,
            payment_method=payment_method,
            user_membership=user_membership,
            description=f"Абонемент через ресепшн: {mem_type.name} для {user.get_full_name() or user.phone_number}",
        )

        return Response({
            'status': 'Абонемент выдан',
            'membership_id': user_membership.id,
            'client': str(user),
            'type': mem_type.name,
            'end_date': end_date.strftime('%Y-%m-%d'),
            'payment_method': payment_method,
        }, status=status.HTTP_201_CREATED)


class AllMembershipsView(generics.ListAPIView):
    """
    GET /api/memberships/all/?client_id=&is_active=
    Все абонементы (ресепшн/админ) с фильтрацией.
    """
    serializer_class = UserMembershipSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        qs = UserMembership.objects.select_related('user', 'membership_type').all()
        client_id = self.request.query_params.get('client_id')
        is_active = self.request.query_params.get('is_active')
        if client_id:
            qs = qs.filter(user_id=client_id)
        if is_active == 'true':
            qs = qs.filter(is_active=True)
        elif is_active == 'false':
            qs = qs.filter(is_active=False)
        return qs.order_by('-start_date')


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
        # 3. Real Logic — деактивируем просроченные перед выдачей
        now = timezone.now()
        UserMembership.objects.filter(
            user=self.request.user,
            is_active=True,
            end_date__lt=now,
        ).update(is_active=False)
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