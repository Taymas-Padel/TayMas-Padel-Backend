import re
import random
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ============================================================
# Максимум неудачных попыток ввода кода до блокировки
# ============================================================
MAX_CODE_ATTEMPTS = 5
CODE_TIMEOUT = 300        # 5 минут жизни кода
BLOCK_TIMEOUT = 600       # 10 минут блокировки после превышения попыток


def normalize_phone(phone):
    """
    Приводит номер к формату +77000000000.
    1. Удаляет всё кроме цифр.
    2. Если начинается с 8 (Казахстан/РФ) → меняет на 7.
    3. Добавляет + в начало.
    4. Проверяет что длина адекватная (10-15 цифр).
    Возвращает None если номер невалиден.
    """
    if not phone:
        return None

    # Оставляем только цифры
    clean_phone = re.sub(r'\D', '', str(phone))

    # Обработка Казахстана/РФ (11 цифр, начинается с 8)
    if len(clean_phone) == 11 and clean_phone.startswith('8'):
        clean_phone = '7' + clean_phone[1:]

    # Проверка длины: минимум 10, максимум 15 цифр
    if len(clean_phone) < 10 or len(clean_phone) > 15:
        return None

    return f"+{clean_phone}"


def send_sms_code(phone_number):
    """
    Генерирует 6-значный код и сохраняет в кэш на 5 минут.
    Проверяет блокировку по количеству попыток.
    Возвращает код (для разработки) или None при ошибке.
    """
    if not phone_number:
        return None

    # Проверяем не заблокирован ли номер за превышение попыток
    block_key = f"sms_blocked_{phone_number}"
    if cache.get(block_key):
        logger.warning(f"SMS blocked for {phone_number} — too many attempts")
        return "BLOCKED"

    # 6-значный код (100000–999999 = 900 000 вариантов)
    code = str(random.randint(100000, 999999))

    # Сохраняем код
    cache.set(f"sms_code_{phone_number}", code, timeout=CODE_TIMEOUT)

    # Сбрасываем счётчик неудачных попыток при новом коде
    cache.set(f"sms_attempts_{phone_number}", 0, timeout=CODE_TIMEOUT)

    # Имитация отправки (в продакшне → SMS-шлюз Kcell/Mobizon)
    logger.info(f"[SMS SERVICE] Code for {phone_number}: {code}")
    print(f"\n📲 [SMS SERVICE] Message to {phone_number}: Your code is {code}\n")

    # TODO: Подключить реальный SMS-шлюз
    # sms_gateway.send(phone_number, f"Ваш код: {code}")

    return code


def verify_sms_code(phone_number, code):
    """
    Сверяет код из кэша. Считает неудачные попытки.
    После MAX_CODE_ATTEMPTS неудачных попыток — блокирует на 10 минут.
    Возвращает: 'OK', 'INVALID', 'EXPIRED', 'BLOCKED'

    В режиме разработки принимает SMS_MASTER_CODE из settings.py
    как универсальный код для любого номера.
    """
    # Мастер-код для разработки (если задан в settings)
    try:
        from django.conf import settings
        master = getattr(settings, 'SMS_MASTER_CODE', '')
        if master and code == master:
            logger.info(f"[SMS] Мастер-код использован для {phone_number}")
            return "OK"
    except Exception:
        pass

    # Проверяем блокировку
    block_key = f"sms_blocked_{phone_number}"
    if cache.get(block_key):
        return "BLOCKED"

    cached_code = cache.get(f"sms_code_{phone_number}")

    # Код истёк или не отправлялся
    if cached_code is None:
        return "EXPIRED"

    # Код правильный
    if cached_code == code:
        # Удаляем код и счётчик — одноразовый
        cache.delete(f"sms_code_{phone_number}")
        cache.delete(f"sms_attempts_{phone_number}")
        return "OK"

    # Код неправильный — считаем попытку
    attempts_key = f"sms_attempts_{phone_number}"
    attempts = cache.get(attempts_key, 0) + 1
    cache.set(attempts_key, attempts, timeout=CODE_TIMEOUT)

    if attempts >= MAX_CODE_ATTEMPTS:
        # Блокируем номер и удаляем код
        cache.set(block_key, True, timeout=BLOCK_TIMEOUT)
        cache.delete(f"sms_code_{phone_number}")
        cache.delete(attempts_key)
        logger.warning(f"Phone {phone_number} blocked after {attempts} failed attempts")
        return "BLOCKED"

    logger.info(f"Failed code attempt for {phone_number}: {attempts}/{MAX_CODE_ATTEMPTS}")
    return "INVALID"