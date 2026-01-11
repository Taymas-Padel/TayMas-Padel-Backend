from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
# 🔥 Импорт для кика старых сессий
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from drf_yasg.utils import swagger_auto_schema

from .utils import send_sms_code, verify_sms_code, normalize_phone
from .serializers import PhoneLoginSerializer, VerifyCodeSerializer
from rest_framework import serializers # <--- Обязательно добавь это
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from drf_yasg import openapi


from rest_framework import generics, filters, permissions
from .models import User
from .serializers import UserPublicSearchSerializer
User = get_user_model()

class SendCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=PhoneLoginSerializer)
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        raw_phone = serializer.validated_data['phone_number']
        phone = normalize_phone(raw_phone)
        
        send_sms_code(phone)
        
        return Response({
            "message": "Код отправлен", 
            "phone": phone 
        })

class MobileLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=VerifyCodeSerializer)
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        raw_phone = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        device_id = serializer.validated_data['device_id'] # <--- Получаем ID

        phone = normalize_phone(raw_phone)

        if not verify_sms_code(phone, code):
            return Response({"error": "Неверный код или срок истек"}, status=400)

        # Ищем или создаем
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={'username': phone, 'role': 'CLIENT'}
        )

        # 🔥 ЛОГИКА ЗАЩИТЫ QR 🔥
        if created:
            # Новый юзер: запоминаем устройство, QR открыт
            user.last_device_id = device_id
            user.is_qr_blocked = False
            user.save()
        else:
            # Старый юзер: проверяем смену устройства
            # Если device_id пришел, и он отличается от сохраненного
            if user.last_device_id and user.last_device_id != device_id:
                user.is_qr_blocked = True  # БЛОКИРУЕМ!
                user.last_device_id = device_id # Запоминаем новое
                user.save()
            elif not user.last_device_id:
                # Если раньше не было ID (старые юзеры), просто сохраняем
                user.last_device_id = device_id
                user.save()

        # 🔥 ЦАРЬ ГОРЫ: Удаляем все старые токены этого юзера
        # Это выкинет юзера с других устройств
        OutstandingToken.objects.filter(user=user).delete()

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "is_new_user": created,
            "role": user.role,
            "user_id": user.id,
            "is_qr_blocked": user.is_qr_blocked # <-- Сообщаем приложению статус
        })
    
# --- 👇 ВСТАВИТЬ В КОНЕЦ ФАЙЛА users/views.py ---


# Специальный сериализатор для менеджера (видит всё, может менять всё)
# ... (твой код выше) ...

# -----------------------------------------------------------
# 👇 ВСТАВЛЯЙ ЭТО В КОНЕЦ ФАЙЛА (С ЗАМЕНОЙ СТАРЫХ ФУНКЦИЙ)
# -----------------------------------------------------------

# Сериализатор оставляем как был
class ManagerUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'phone_number', 'first_name', 'last_name', 'avatar', 'is_qr_blocked', 'last_device_id', 'role')

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
    responses={200: ManagerUserSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def search_user_view(request):
    """
    Поиск клиента по номеру телефона.
    """
    phone = request.query_params.get('phone')
    if not phone:
        return Response({"error": "Укажите параметр phone"}, status=400)
    
    users = User.objects.filter(phone_number__icontains=phone)
    serializer = ManagerUserSerializer(users, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['action'],
        properties={
            'action': openapi.Schema(type=openapi.TYPE_STRING, description="unblock_qr / update_info"),
            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="Новое имя (если update_info)"),
            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="Новая фамилия (если update_info)"),
        }
    ),
    responses={200: "Успех"}
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def manager_user_action_view(request, pk):
    """
    Действия менеджера: разблок QR или смена имени.
    """
    user = get_object_or_404(User, pk=pk)
    action = request.data.get('action')

    if action == 'unblock_qr':
        user.is_qr_blocked = False
        user.save()
        return Response({
            "status": "success", 
            "message": "QR-код разблокирован.",
            "is_qr_blocked": False
        })

    elif action == 'update_info':
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        
        if first_name: user.first_name = first_name
        if last_name: user.last_name = last_name
        
        user.save()
        return Response({
            "status": "success",
            "message": "Данные обновлены",
            "user": {"first_name": user.first_name, "last_name": user.last_name}
        })

    return Response({"error": "Неизвестное действие"}, status=400)



class UserSearchView(generics.ListAPIView):
    # 1. Используем наш безопасный сериализатор (без QR)
    serializer_class = UserPublicSearchSerializer
    
    # 2. Разрешаем доступ авторизованным (или AllowAny, если поиск открытый)
    permission_classes = [permissions.AllowAny] 

    # 3. Базовый запрос (берем всех активных юзеров, например)
    queryset = User.objects.all() # Можно добавить .filter(is_active=True)

    # 4. ВОТ ЭТО добавит поле в Swagger!
    filter_backends = [filters.SearchFilter]
    
    # 5. Указываем, по каким полям искать (никнейм, имя)
    search_fields = ['username', 'first_name', 'last_name']
