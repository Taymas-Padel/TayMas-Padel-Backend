import urllib.parse
import logging
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_jwt(token):
    """
    Проверяет JWT токен и возвращает пользователя.
    """
    try:
        auth = JWTAuthentication()
        validated_token = auth.get_validated_token(token)
        user = auth.get_user(validated_token)
        if user and user.is_active:
            return user
        return AnonymousUser()
    except (InvalidToken, TokenError):
        # Если токен истек или невалиден, не пишем сам токен в логи (безопасность)
        logger.warning("WebSocket auth failed: Invalid or expired token.")
        return AnonymousUser()
    except Exception as e:
        logger.error("WebSocket auth unexpected error.")
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    """
    Middleware для извлечения JWT токена из query параметров (url).
    """
    async def __call__(self, scope, receive, send):
        # Получаем строку запроса (все, что после '?' в URL)
        query_string = scope.get("query_string", b"").decode("utf-8")
        # Парсим параметры в словарь
        query_params = urllib.parse.parse_qs(query_string)
        
        # Достаем параметр token (если его нет, берем None)
        token = query_params.get("token", [None])[0]

        if token:
            scope["user"] = await get_user_from_jwt(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)