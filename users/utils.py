import random
from django.core.cache import cache
import random
import re  # <--- Не забудь импортировать re (Regular Expressions)
def normalize_phone(phone):
    """
    Приводит номер к формату +77000000000.
    1. Удаляет скобки, пробелы, тире.
    2. Если начинается с 87... -> меняет на 77...
    3. Добавляет + в начало.
    """
    if not phone:
        return None

    # 1. Оставляем только цифры
    # Было: "+7 (701) 123-45-67" -> Стало: "77011234567"
    clean_phone = re.sub(r'\D', '', str(phone))

    # 2. Обработка Казахстана/РФ (11 цифр)
    if len(clean_phone) == 11:
        # Если начинается с 8 (например 8701...), меняем первую цифру на 7
        if clean_phone.startswith('8'):
            clean_phone = '7' + clean_phone[1:]
    
    # 3. Добавляем плюс, если это стандартный формат
    # Итог: +77011234567
    return f"+{clean_phone}"
def send_sms_code(phone_number):
    """
    Генерирует код и сохраняет его в кэш (Redis/Memory) на 5 минут.
    """
    if not phone_number:
        return False

    # 1. Генерируем 4 цифры
    code = str(random.randint(1000, 9999))
    
    # 2. Сохраняем: Ключ = Телефон, Значение = Код, Время = 300 сек
    cache.set(f"sms_code_{phone_number}", code, timeout=300)
    
    # 3. Имитация отправки (СМОТРИ В ТЕРМИНАЛ)
    print(f"\n📲 [SMS SERVICE] Message to {phone_number}: Your code is {code}\n")
    
    # TODO: Потом здесь подключим реальный SMS-шлюз (Kcell/Mobizon)
    return code

def verify_sms_code(phone_number, code):
    """
    Сверяет код из кэша с тем, что ввел юзер.
    """
    cached_code = cache.get(f"sms_code_{phone_number}")
    
    if cached_code == code:
        # Удаляем код, чтобы нельзя было использовать дважды
        cache.delete(f"sms_code_{phone_number}")
        return True
    return False