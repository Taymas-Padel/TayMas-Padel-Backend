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


# --------------------------------------------------------------------------
# 1. Каталог абонементов (публичный)
# --------------------------------------------------------------------------

class MembershipTypeListView(generics.ListAPIView):
    """GET /api/memberships/types/ — только активные, для витрины."""
    queryset = MembershipType.objects.filter(is_active=True)
    serializer_class = MembershipTypeSerializer
    permission_classes = [permissions.AllowAny]


# --------------------------------------------------------------------------
# 1b. Управление типами (ADMIN / Ресепшн)
# --------------------------------------------------------------------------

class MembershipTypeManageView(generics.ListCreateAPIView):
    """GET/POST /api/memberships/types/manage/"""
    queryset = MembershipType.objects.all().order_by('service_type', 'name')
    serializer_class = MembershipTypeSerializer
    permission_classes = [IsReceptionist]


class MembershipTypeManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/memberships/types/manage/<id>/"""
    queryset = MembershipType.objects.all()
    serializer_class = MembershipTypeSerializer
    permission_classes = [IsReceptionist]


# --------------------------------------------------------------------------
# 2. Покупка абонемента (клиент сам)
# --------------------------------------------------------------------------

class BuyMembershipView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        mem_type = get_object_or_404(MembershipType, pk=pk, is_active=True)
        user = request.user

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
            payment_method=Transaction.PaymentMethod.KASPI,
            user_membership=user_membership,
            description=f"Покупка абонемента: {mem_type.name}",
        )

        return Response({
            "status": "Абонемент успешно куплен!",
            "membership_id": user_membership.id,
        }, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------
# 3. Покупка через ресепшн
# --------------------------------------------------------------------------

class ReceptionBuyMembershipView(APIView):
    """
    POST /api/memberships/reception/buy/
    Body: { client_id, membership_type_id, payment_method }
    """
    permission_classes = [IsReceptionist]

    def post(self, request):
        from users.models import User

        client_id = request.data.get('client_id')
        type_id = request.data.get('membership_type_id')
        payment_method = request.data.get('payment_method', Transaction.PaymentMethod.CASH)

        if not client_id or not type_id:
            return Response(
                {'error': 'Укажите client_id и membership_type_id'}, status=400,
            )

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
            description=(
                f"Абонемент через ресепшн: {mem_type.name} "
                f"для {user.get_full_name() or user.phone_number}"
            ),
        )

        serializer = UserMembershipSerializer(user_membership)

        return Response({
            'status': 'Абонемент выдан',
            'membership': serializer.data,
        }, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------
# 4. Список всех абонементов (CRM)
# --------------------------------------------------------------------------

class AllMembershipsView(generics.ListAPIView):
    """
    GET /api/memberships/all/?client_id=&is_active=&service_type=
    """
    serializer_class = UserMembershipSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        qs = UserMembership.objects.select_related('user', 'membership_type').all()

        client_id = self.request.query_params.get('client_id')
        is_active = self.request.query_params.get('is_active')
        service_type = self.request.query_params.get('service_type')

        if client_id:
            qs = qs.filter(user_id=client_id)
        if is_active == 'true':
            qs = qs.filter(is_active=True)
        elif is_active == 'false':
            qs = qs.filter(is_active=False)
        if service_type:
            qs = qs.filter(membership_type__service_type=service_type.upper())

        return qs.order_by('-start_date')


# --------------------------------------------------------------------------
# 5. ViewSet для пользователя (Мои абонементы)
# --------------------------------------------------------------------------

class UserMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return UserMembership.objects.none()
        if not self.request.user.is_authenticated:
            return UserMembership.objects.none()

        now = timezone.now()
        UserMembership.objects.filter(
            user=self.request.user,
            is_active=True,
            end_date__lt=now,
        ).update(is_active=False)

        return UserMembership.objects.filter(
            user=self.request.user,
        ).select_related('membership_type')

    # ЗАМОРОЗКА
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

    # РАЗМОРОЗКА
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
            "new_end_date": membership.end_date.strftime('%Y-%m-%d'),
        })

    # ИСТОРИЯ СПИСАНИЙ
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        membership = self.get_object()
        from finance.serializers import TransactionSerializer

        transactions = Transaction.objects.filter(
            user_membership=membership,
        ).order_by('-created_at')

        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
