import logging
from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import get_object_or_404

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
)
from .permissions import IsReceptionist
from django.db.models import Q
# Убедись, что импортирован сериализатор (или используй UserShortSerializer)
from .serializers import UserPublicSearchSerializer
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
    serializer = ReceptionistUserSerializer(user)
    return Response(serializer.data)


# =============================================
# 7. ПУБЛИЧНЫЙ ПОИСК (приложение — друзья)
# =============================================

class UserSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('search')
        
        # Если поиска нет — возвращаем пустой список
        if not query:
            return Response([])

        # 1. Сначала фильтруем (Имя ИЛИ Фамилия ИЛИ Телефон ИЛИ Никнейм)
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone_number__icontains=query)
        ).distinct()

        # 2. И только ПОТОМ обрезаем (например, топ-20 результатов)
        users = users[:20]

        # 3. Отдаем результат
        serializer = UserPublicSearchSerializer(users, many=True)
        return Response(serializer.data)