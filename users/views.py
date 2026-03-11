import logging
from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count

from rest_framework import status, permissions, generics, filters, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .utils import send_sms_code, verify_sms_code, normalize_phone
from .serializers import (
    PhoneLoginSerializer,
    VerifyCodeSerializer,
    CRMLoginSerializer,
    UserPublicSearchSerializer,
    ReceptionistUserSerializer,
    CoachListSerializer,
    PublicUserProfileSerializer,
    _get_league,
)
from .permissions import IsReceptionist

logger = logging.getLogger(__name__)

User = get_user_model()


# =============================================
# THROTTLE — Защита от перебора
# =============================================

class SendSMSThrottle(AnonRateThrottle):
    """Максимум 3 запроса SMS в минуту с одного IP"""
    rate = '3/min'


class VerifyCodeThrottle(AnonRateThrottle):
    """Максимум 5 попыток ввода кода в минуту с одного IP"""
    rate = '5/min'


# =============================================
# 1. ОТПРАВКА SMS-КОДА (мобильное приложение)
# =============================================

class SendCodeView(APIView):
    """
    POST /api/auth/mobile/send-code/
    Отправляет 6-значный SMS-код на номер телефона.
    Для клиентов и тренеров.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SendSMSThrottle]

    @swagger_auto_schema(request_body=PhoneLoginSerializer)
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        raw_phone = serializer.validated_data['phone_number']
        phone = normalize_phone(raw_phone)

        if not phone:
            return Response(
                {"error": "Неверный формат номера телефона"},
                status=400
            )

        result = send_sms_code(phone)

        if result == "BLOCKED":
            return Response(
                {"error": "Слишком много попыток. Попробуйте через 10 минут."},
                status=429
            )

        return Response({
            "message": "Код отправлен",
            "phone": phone
        })


# =============================================
# 2. ПОДТВЕРЖДЕНИЕ КОДА + ВХОД (мобильное приложение)
# =============================================

class MobileLoginView(APIView):
    """
    POST /api/auth/mobile/login/
    Проверяет SMS-код → возвращает JWT-токены.
    Создаёт нового пользователя если его нет в базе.
    Блокирует QR при смене устройства.
    
    ВАЖНО: Админы и ресепшн НЕ могут входить через SMS.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [VerifyCodeThrottle]

    @swagger_auto_schema(request_body=VerifyCodeSerializer)
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        raw_phone = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        device_id = serializer.validated_data['device_id']

        phone = normalize_phone(raw_phone)
        if not phone:
            return Response(
                {"error": "Неверный формат номера телефона"},
                status=400
            )

        # Проверяем код
        result = verify_sms_code(phone, code)

        if result == "BLOCKED":
            return Response(
                {"error": "Слишком много неудачных попыток. Номер заблокирован на 10 минут."},
                status=429
            )
        elif result == "EXPIRED":
            return Response(
                {"error": "Код истёк или не был отправлен. Запросите новый."},
                status=400
            )
        elif result == "INVALID":
            return Response(
                {"error": "Неверный код. Попробуйте ещё раз."},
                status=400
            )

        # Код верный — ищем или создаём пользователя
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                'username': phone,
                'role': User.Role.CLIENT,
            }
        )

        # Новый юзер — ставим неиспользуемый пароль (вход только по SMS)
        if created:
            user.set_unusable_password()
            user.last_device_id = device_id
            user.is_qr_blocked = False
            user.save()
            logger.info(f"New user created: {phone}")
        else:
            # Проверяем: админы и ресепшн не входят через SMS
            if not user.can_login_via_sms:
                return Response(
                    {"error": "Для вашей роли используйте вход по логину и паролю в CRM."},
                    status=403
                )

            # Проверяем смену устройства → блокировка QR
            if user.last_device_id and user.last_device_id != device_id:
                user.is_qr_blocked = True
                logger.info(f"QR blocked for user {user.id} — device changed")
            
            if not user.last_device_id:
                # Старый юзер без device_id — просто сохраняем
                pass

            user.last_device_id = device_id
            user.save()

        # Удаляем старые МОБИЛЬНЫЕ токены этого юзера
        # (чтобы не выбивать CRM-сессию если юзер — тренер)
        OutstandingToken.objects.filter(user=user).delete()

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "is_new_user": created,
            "is_profile_complete": user.is_profile_complete,
            "role": user.role,
            "user_id": user.id,
            "is_qr_blocked": user.is_qr_blocked,
        })


# =============================================
# 3. ВХОД В CRM (ресепшн / админ — по паролю)
# =============================================

class CRMLoginView(APIView):
    """
    POST /api/auth/crm/login/
    Вход в CRM-систему по логину + паролю.
    Только для ролей: ADMIN, RECEPTIONIST.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=CRMLoginSerializer)
    def post(self, request):
        serializer = CRMLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Пробуем найти по username, если не нашли — по телефону
        user = authenticate(username=username, password=password)

        if not user:
            # Попробуем по телефону
            phone = normalize_phone(username)
            if phone:
                try:
                    phone_user = User.objects.get(phone_number=phone)
                    if phone_user.check_password(password):
                        user = phone_user
                except User.DoesNotExist:
                    pass

        if not user:
            return Response(
                {"error": "Неверный логин или пароль."},
                status=401
            )

        if not user.is_active:
            return Response(
                {"error": "Аккаунт деактивирован. Обратитесь к администратору."},
                status=403
            )

        # Проверяем роль — только админ и ресепшн
        if not user.can_login_to_crm:
            return Response(
                {"error": "У вас нет доступа к CRM. Используйте мобильное приложение."},
                status=403
            )

        refresh = RefreshToken.for_user(user)

        logger.info(f"CRM login: {user.username} (role={user.role})")

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        })


# =============================================
# 4. РЕСЕПШН — Поиск клиента по телефону
# =============================================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'phone',
            openapi.IN_QUERY,
            description="Номер телефона (или часть номера)",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={200: ReceptionistUserSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsReceptionist])
def receptionist_search_view(request):
    """
    GET /api/auth/reception/search/?phone=7700
    Поиск клиента по номеру телефона.
    Доступно только для ресепшн и администраторов.
    """
    phone = request.query_params.get('phone', '').strip()
    if not phone or len(phone) < 4:
        return Response(
            {"error": "Введите минимум 4 символа номера телефона"},
            status=400
        )

    # Ресепшн видит ТОЛЬКО клиентов — не тренеров, не админов, не других ресепшн
    users = User.objects.filter(
        phone_number__icontains=phone,
        role=User.Role.CLIENT,
    )[:20]
    serializer = ReceptionistUserSerializer(users, many=True)
    return Response(serializer.data)


# =============================================
# 5. РЕСЕПШН — Действия с клиентом
# =============================================

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['action'],
        properties={
            'action': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="unblock_qr / update_info / deactivate / activate"
            ),
            'first_name': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Новое имя (если action=update_info)"
            ),
            'last_name': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Новая фамилия (если action=update_info)"
            ),
        }
    ),
    responses={200: "Успех"}
)
@api_view(['POST'])
@permission_classes([IsReceptionist])
def receptionist_action_view(request, pk):
    """
    POST /api/auth/reception/user/{id}/action/
    Действия ресепшн: разблок QR, смена имени, деактивация.
    """
    user = get_object_or_404(User, pk=pk)
    action = request.data.get('action')

    # Ресепшн может управлять ТОЛЬКО клиентами
    if user.role != User.Role.CLIENT:
        return Response(
            {"error": "Вы можете управлять только клиентами."},
            status=403
        )

    if action == 'unblock_qr':
        user.is_qr_blocked = False
        user.save(update_fields=['is_qr_blocked'])
        logger.info(f"QR unblocked for user {user.id} by {request.user.username}")
        return Response({
            "status": "success",
            "message": f"QR-код разблокирован для {user.first_name or user.phone_number}.",
            "is_qr_blocked": False
        })

    elif action == 'update_info':
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name

        user.save(update_fields=['first_name', 'last_name', 'updated_at'])
        logger.info(f"User {user.id} info updated by {request.user.username}")
        return Response({
            "status": "success",
            "message": "Данные обновлены.",
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        })

    elif action == 'deactivate':
        user.is_active = False
        user.save(update_fields=['is_active'])
        logger.info(f"User {user.id} deactivated by {request.user.username}")
        return Response({
            "status": "success",
            "message": f"Аккаунт {user.first_name or user.phone_number} деактивирован.",
        })

    elif action == 'activate':
        user.is_active = True
        user.save(update_fields=['is_active'])
        logger.info(f"User {user.id} activated by {request.user.username}")
        return Response({
            "status": "success",
            "message": f"Аккаунт {user.first_name or user.phone_number} активирован.",
        })

    return Response(
        {"error": f"Неизвестное действие: {action}. Доступны: unblock_qr, update_info, deactivate, activate."},
        status=400
    )


# =============================================
# 6. ПРОСМОТР ДАННЫХ КЛИЕНТА (ресепшн)
# =============================================

@swagger_auto_schema(
    method='get',
    responses={200: ReceptionistUserSerializer()}
)
@api_view(['GET'])
@permission_classes([IsReceptionist])
def receptionist_user_detail_view(request, pk):
    """
    GET /api/auth/reception/user/{id}/
    Просмотр полных данных клиента ресепшн.
    """
    user = get_object_or_404(User, pk=pk)
    serializer = ReceptionistUserSerializer(user, context={'request': request})
    return Response(serializer.data)


# =============================================
# 7. ПУБЛИЧНЫЙ ПОИСК (приложение — друзья)
# =============================================

class UserSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('search')
        if not query:
            return Response([])

        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone_number__icontains=query)
        ).exclude(id=request.user.id).distinct()[:20]

        serializer = UserPublicSearchSerializer(users, many=True)
        return Response(serializer.data)


# =============================================
# 8. СПИСОК ВСЕХ КЛИЕНТОВ (CRM — ресепшн/админ)
# =============================================

class ClientListView(generics.ListAPIView):
    """
    GET /api/auth/clients/?search=&role=
    Список клиентов для CRM. Поддерживает поиск по имени/телефону и фильтр по роли.
    """
    serializer_class = ReceptionistUserSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        qs = User.objects.all().order_by('-created_at')

        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(phone_number__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search)
            )

        role = self.request.query_params.get('role', '').upper()
        if role:
            qs = qs.filter(role=role)
        else:
            # По умолчанию показываем клиентов и тренеров
            qs = qs.filter(role__in=['CLIENT', 'COACH_PADEL', 'COACH_FITNESS'])

        return qs.distinct()


# =============================================
# 8b. СПИСОК ТРЕНЕРОВ (для брони и приложения)
# =============================================

class CoachesListView(generics.ListAPIView):
    """
    GET /api/auth/coaches/
    Список тренеров (падел + фитнес) для выбора в брони. Доступно всем.
    """
    serializer_class = CoachListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return User.objects.filter(
            role__in=['COACH_PADEL', 'COACH_FITNESS']
        ).order_by('role', 'first_name', 'last_name')


# =============================================
# 8c. ОБНОВЛЕНИЕ FCM ТОКЕНА (для пуш-уведомлений)
# =============================================

class UpdateFCMTokenView(APIView):
    """
    POST /api/auth/me/fcm/
    Сохранить FCM token для пуш-уведомлений (вызвать после логина в мобилке).
    Body: { "fcm_token": "..." } или { "fcm_token": null } чтобы сбросить.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        if token is not None and not isinstance(token, str):
            token = str(token).strip() or None
        request.user.fcm_token = token
        request.user.save(update_fields=['fcm_token'])
        return Response({"status": "ok", "fcm_token_saved": token is not None})


# =============================================
# 9. ПРОФИЛЬ: ПЕРСОНАЛЬНАЯ СТАТИСТИКА (мобилка)
# =============================================

class MyStatsView(APIView):
    """
    GET /api/auth/me/stats/
    Персональная статистика клиента: брони, матчи, абонемент, часы на корте.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from bookings.models import Booking
        from gamification.models import Match
        from memberships.models import UserMembership
        from gym.models import GymVisit
        from django.db.models import F, ExpressionWrapper, DurationField

        user = request.user
        now = timezone.now()

        # Брони
        all_bookings = Booking.objects.filter(
            Q(user=user) | Q(participants=user)
        ).distinct()
        upcoming_bookings = all_bookings.filter(
            end_time__gte=now
        ).exclude(status='CANCELED').order_by('start_time')[:5]

        total_bookings = all_bookings.exclude(status='CANCELED').count()
        completed_bookings = all_bookings.filter(status='COMPLETED').count()

        # Часы на корте
        confirmed = all_bookings.filter(status__in=['CONFIRMED', 'COMPLETED'])
        total_hours = 0.0
        for b in confirmed:
            total_hours += (b.end_time - b.start_time).total_seconds() / 3600

        # Матчи
        matches_count = Match.objects.filter(
            Q(team_a=user) | Q(team_b=user)
        ).distinct().count()
        wins_count = Match.objects.filter(
            Q(team_a=user, winner_team='A') | Q(team_b=user, winner_team='B')
        ).distinct().count()

        # Активный абонемент
        membership_data = None
        active_mem = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            end_date__gte=now,
        ).select_related('membership_type').first()
        if active_mem:
            membership_data = {
                "id": active_mem.id,
                "name": active_mem.membership_type.name,
                "type": active_mem.membership_type.service_type,
                "end_date": active_mem.end_date.strftime('%d.%m.%Y'),
                "hours_remaining": float(active_mem.hours_remaining),
                "visits_remaining": active_mem.visits_remaining,
                "is_frozen": active_mem.is_frozen,
            }

        # Посещения зала
        gym_visits = GymVisit.objects.filter(user=user).count()

        # Ближайшие брони (сериализуем вручную)
        upcoming_list = []
        for b in upcoming_bookings:
            upcoming_list.append({
                "id": b.id,
                "court": b.court.name,
                "start_time": timezone.localtime(b.start_time).strftime('%d.%m.%Y %H:%M'),
                "end_time": timezone.localtime(b.end_time).strftime('%H:%M'),
                "status": b.status,
                "coach": b.coach.first_name if b.coach else None,
            })

        return Response({
            "user": {
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "phone": user.phone_number,
                "role": user.role,
                "rating_elo": user.rating_elo,
                "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                "is_profile_complete": user.is_profile_complete,
            },
            "stats": {
                "total_bookings": total_bookings,
                "completed_bookings": completed_bookings,
                "total_hours_on_court": round(total_hours, 1),
                "matches_played": matches_count,
                "matches_won": wins_count,
                "gym_visits": gym_visits,
            },
            "active_membership": membership_data,
            "upcoming_bookings": upcoming_list,
        })


# =============================================
# 10. HOME DASHBOARD (главный экран мобилки)
# =============================================

class HomeDashboardView(APIView):
    """
    GET /api/auth/home/
    Главный экран мобильного приложения: приветствие, брони, абонемент, акции.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from bookings.models import Booking
        from memberships.models import UserMembership
        from marketing.models import Promotion
        from news.models import NewsItem
        from django.db.models import Q

        user = request.user
        now = timezone.now()

        # Ближайшая бронь
        next_booking = Booking.objects.filter(
            Q(user=user) | Q(participants=user),
            end_time__gte=now,
            status__in=['CONFIRMED', 'PENDING'],
        ).distinct().order_by('start_time').first()

        next_booking_data = None
        if next_booking:
            local_start = timezone.localtime(next_booking.start_time)
            local_end = timezone.localtime(next_booking.end_time)
            next_booking_data = {
                "id": next_booking.id,
                "court": next_booking.court.name,
                "date": local_start.strftime('%d.%m.%Y'),
                "start_time": local_start.strftime('%H:%M'),
                "end_time": local_end.strftime('%H:%M'),
                "status": next_booking.status,
            }

        # Активный абонемент
        membership_data = None
        active_mem = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            end_date__gte=now,
        ).select_related('membership_type').first()
        if active_mem:
            days_left = (active_mem.end_date - now).days
            membership_data = {
                "name": active_mem.membership_type.name,
                "type": active_mem.membership_type.service_type,
                "end_date": timezone.localtime(active_mem.end_date).strftime('%d.%m.%Y'),
                "days_left": max(0, days_left),
                "hours_remaining": float(active_mem.hours_remaining),
                "visits_remaining": active_mem.visits_remaining,
                "is_frozen": active_mem.is_frozen,
            }

        # Активные акции (топ-3)
        promos = Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
        ).order_by('-priority')[:3]
        promos_data = [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "image_url": p.image_url,
                "promo_code": p.promo_code,
            }
            for p in promos
        ]

        # Новости клуба (топ-5 свежих)
        news = NewsItem.objects.filter(
            is_published=True
        ).order_by('-created_at')[:5]
        news_data = [
            {
                "id": n.id,
                "title": n.title,
                "preview": n.content[:120] + '...' if len(n.content) > 120 else n.content,
                "category": n.category,
                "image_url": n.image_url,
                "created_at": n.created_at.strftime('%d.%m.%Y'),
            }
            for n in news
        ]

        full_name = f"{user.first_name} {user.last_name}".strip()

        from users.serializers import _get_league
        league = _get_league(user.rating_elo)

        return Response({
            "greeting": f"Привет, {user.first_name or 'друг'}!",
            "user": {
                "id": user.id,
                "full_name": full_name or user.username,
                "phone": user.phone_number,
                "rating_elo": user.rating_elo,
                "league": league,
                "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                "is_profile_complete": user.is_profile_complete,
            },
            "next_booking": next_booking_data,
            "active_membership": membership_data,
            "promotions": promos_data,
            "news": news_data,
        })


# =============================================
# 11. ПУБЛИЧНЫЙ ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# =============================================

class PublicUserProfileView(APIView):
    """
    GET /api/auth/users/<id>/profile/
    Публичный профиль пользователя: имя, ELO, лига, статистика, совместные матчи с текущим юзером.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from gamification.models import Match
        from bookings.models import Booking
        from users.serializers import PublicUserProfileSerializer, _get_league

        target = get_object_or_404(User, pk=pk)
        me = request.user

        data = PublicUserProfileSerializer(target, context={'request': request}).data

        # Совместные матчи
        joint_matches = Match.objects.filter(
            Q(team_a=me) | Q(team_b=me)
        ).filter(
            Q(team_a=target) | Q(team_b=target)
        ).distinct().order_by('-date')[:10]
        joint_list = []
        for m in joint_matches:
            in_a_me = me in m.team_a.all()
            in_a_target = target in m.team_a.all()
            same_team = in_a_me == in_a_target
            joint_list.append({
                "id": m.id,
                "date": m.date.strftime('%d.%m.%Y'),
                "score": m.score,
                "winner_team": m.winner_team,
                "same_team": same_team,
            })
        data['joint_matches'] = joint_list

        return Response(data)


# =============================================
# 12. УДАЛЕНИЕ АККАУНТА
# =============================================

class AccountDeleteView(APIView):
    """
    DELETE /api/auth/me/delete/
    Удаление собственного аккаунта. Требует подтверждения: body { "confirm": true }.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        confirm = request.data.get('confirm')
        if not confirm:
            return Response(
                {"detail": "Передайте { \"confirm\": true } для подтверждения удаления аккаунта."},
                status=400,
            )
        user = request.user
        user.delete()
        return Response({"status": "Аккаунт удалён."}, status=204)


# =============================================
# 13. ЛИГА / РАНГ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
# =============================================

class MyLeagueView(APIView):
    """
    GET /api/auth/me/league/
    Текущая лига, ELO, прогресс до следующей лиги.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from users.serializers import _get_league
        user = request.user
        elo = user.rating_elo
        current = _get_league(elo)

        LEAGUES = [
            {"name": "Новичок",  "min_elo": 0,    "max_elo": 999},
            {"name": "Бронза",   "min_elo": 1000,  "max_elo": 1199},
            {"name": "Серебро",  "min_elo": 1200,  "max_elo": 1399},
            {"name": "Золото",   "min_elo": 1400,  "max_elo": 1599},
            {"name": "Платина",  "min_elo": 1600,  "max_elo": 1799},
            {"name": "Элита",    "min_elo": 1800,  "max_elo": 9999},
        ]
        # Найти следующую лигу
        next_league = None
        progress_pct = 100
        for i, lg in enumerate(LEAGUES):
            if lg['name'] == current['name'] and i + 1 < len(LEAGUES):
                next_league = LEAGUES[i + 1]
                span = next_league['min_elo'] - lg['min_elo']
                gained = elo - lg['min_elo']
                progress_pct = round(min(100, gained / span * 100)) if span else 100
                break

        return Response({
            "rating_elo": elo,
            "current_league": current,
            "next_league": next_league,
            "progress_to_next": progress_pct,
            "elo_needed": (next_league['min_elo'] - elo) if next_league else 0,
        })