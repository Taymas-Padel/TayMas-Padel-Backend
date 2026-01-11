from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Booking, BookingService
from django.contrib.auth import get_user_model
from inventory.models import Service
from finance.models import Transaction
from core.models import ClubSetting, ClosedDay
from memberships.models import UserMembership
from decimal import Decimal
from marketing.models import Promotion # Импорт нашей новой модели

User = get_user_model()

# --- 1. Сериализатор для проверки доступности слотов ---
class SlotAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    court_id = serializers.IntegerField(required=False)


# --- 2. Сериализаторы для ПРОСМОТРА (GET) ---

class BookingServiceSerializer(serializers.ModelSerializer):
    """Показывает услуги внутри брони (для чтения)"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = BookingService
        fields = ['service_name', 'quantity', 'price_at_moment']

class BookingSerializer(serializers.ModelSerializer):
    """Стандартный сериализатор для просмотра списка броней"""
    court_name = serializers.CharField(source='court.name', read_only=True)
    coach_name = serializers.CharField(source='coach.username', read_only=True, allow_null=True)
    services = BookingServiceSerializer(many=True, read_only=True) # Показываем купленные услуги
# 🔥 Добавляем отображение друзей (можно просто имена)
    participants_names = serializers.SlugRelatedField(
        many=True, 
        read_only=True, 
        slug_field='username', # Или 'first_name'
        source='participants'
    )
    class Meta:
        model = Booking
        # 👇 ВЫ ЗАБЫЛИ ДОБАВИТЬ ЭТО В СПИСОК НИЖЕ
        fields = [
            'id', 
            'court', 
            'court_name', 
            'start_time', 
            'end_time', 
            'price', 
            'status', 
            'coach', 
            'coach_name', 
            'services', 
            'participants_names' # <--- ДОБАВЬТЕ СЮДА ЗАПЯТУЮ И ЭТО ПОЛЕ
        ]

# --- 3. Сериализаторы для СОЗДАНИЯ (POST) ---

class BookingServiceInputSerializer(serializers.Serializer):
    """Вспомогательный для приема списка услуг при создании"""
    service_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)

class CreateBookingSerializer(serializers.ModelSerializer):
    """Сложный сериализатор для создания брони с расчетами"""
    duration = serializers.IntegerField(write_only=True)
    promo_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='COACH_PADEL'),
        required=False, 
        allow_null=True
    )
    
    # Принимаем список услуг
    services = BookingServiceInputSerializer(many=True, required=False, write_only=True)
# 🔥 НОВОЕ ПОЛЕ ДЛЯ ВХОДА (Список ID друзей)
    friends_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    # 🔥🔥🔥 ДОБАВИТЬ ВОТ ЭТО ПОЛЕ СЮДА (ты забыл его скопировать) 🔥🔥🔥
    participants_names = serializers.SlugRelatedField(
        many=True, 
        read_only=True, 
        slug_field='username', # Или 'phone_number', если хочешь видеть номера
        source='participants'
    )
    class Meta:
        model = Booking
        # 👇 ТЕБЕ НУЖНО ДОБАВИТЬ 'promo_code' В ЭТОТ СПИСОК
        fields = [
            'id', 
            'court', 
            'start_time', 
            'duration', 
            'services', 
            'coach', 
            'price', 
            'status',
            'promo_code',
            'friends_ids',
            'participants_names'  # <--- ДОБАВЬ ЭТУ СТРОЧКУ
        ]
        read_only_fields = ['id', 'price', 'end_time', 'status']

    def validate(self, data):
        court = data['court']
        start_time = data['start_time']
        duration = data['duration']
        coach = data.get('coach')

        end_time = start_time + timedelta(minutes=duration)

        # 1. ПРОВЕРКА: Нельзя в прошлое
        if start_time < timezone.now():
            raise serializers.ValidationError("Нельзя забронировать время в прошлом.")

        # 2. ПРОВЕРКА: Выходные / Праздники (НОВОЕ!) 🛑
        # Проверяем, есть ли дата начала брони в списке "Закрытых дней"
        if ClosedDay.objects.filter(date=start_time.date()).exists():
            # Достаем причину, чтобы красиво ответить клиенту
            closed_day = ClosedDay.objects.get(date=start_time.date())
            raise serializers.ValidationError(
                f"В этот день клуб закрыт. Причина: {closed_day.reason or 'Санитарный день'}."
            )
        friends_ids = data.get('friends_ids', [])
        if len(friends_ids) > 3:
            raise serializers.ValidationError("Можно добавить максимум 3 друзей.")
            
        # (Опционально) Проверка, что нельзя добавить самого себя
        if self.context['request'].user.id in friends_ids:
             raise serializers.ValidationError("Не нужно добавлять себя в список друзей, вы и так организатор.")
        # # 3. ПРОВЕРКА: График работы (Учитываем ДЛИТЕЛЬНОСТЬ) ⏰
        open_setting = ClubSetting.objects.filter(key='OPEN_TIME').first()
        close_setting = ClubSetting.objects.filter(key='CLOSE_TIME').first()

        open_hour = int(open_setting.value.split(':')[0]) if open_setting else 7
        close_hour = int(close_setting.value.split(':')[0]) if close_setting else 23

        # Создаем объекты времени открытия и закрытия ДЛЯ КОНКРЕТНО ЭТОГО ДНЯ
        # Мы берем дату из start_time и подставляем часы открытия/закрытия
        club_open_time = start_time.replace(hour=open_hour, minute=0, second=0, microsecond=0)
        club_close_time = start_time.replace(hour=close_hour, minute=0, second=0, microsecond=0)

        # А. Проверяем начало: Нельзя прийти раньше открытия
        if start_time < club_open_time:
             raise serializers.ValidationError(
                 f"Клуб закрыт. Мы открываемся в {open_hour}:00."
             )

        # Б. Проверяем КОНЕЦ: Игра должна закончиться ДО закрытия
        # Если (Начало + Длительность) > Времени Закрытия -> Ошибка
        if end_time > club_close_time:
             # Считаем, сколько минут лишних, чтобы сказать клиенту
             diff = end_time - club_close_time
             extra_minutes = int(diff.total_seconds() / 60)
             
             raise serializers.ValidationError(
                 f"Ваша игра заканчивается в {end_time.strftime('%H:%M')}, но клуб закрывается в {close_hour}:00. "
                 f"Пожалуйста, выберите время пораньше или сократите длительность."
             )

        # 4. ПРОВЕРКА: Занятость корта
        court_conflicts = Booking.objects.filter(
            court=court,
            status__in=['CONFIRMED', 'PENDING'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        if court_conflicts.exists():
            raise serializers.ValidationError("К сожалению, этот корт уже занят.")

        # 5. ПРОВЕРКА: Занятость тренера
        if coach:
            coach_conflicts = Booking.objects.filter(
                coach=coach,
                status__in=['CONFIRMED', 'PENDING'],
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            if coach_conflicts.exists():
                raise serializers.ValidationError(f"Тренер {coach.first_name or coach.username} уже занят.")

        data['calculated_end_time'] = end_time
    
        return data
    
    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        duration = validated_data.pop('duration')
        end_time = validated_data.pop('calculated_end_time')
        friends_ids = validated_data.pop('friends_ids', [])
        court = validated_data['court']
        coach = validated_data.get('coach')
        user = validated_data['user'] # Нам нужен юзер для поиска абонемента

        # --- 0. ПОДГОТОВКА (Часы) ---
        # Используем Decimal для точности (чтобы не было 9.99999 часов)
        hours = Decimal(duration) / Decimal(60)

        # --- 🔥 1. ЛОГИКА АБОНЕМЕНТА (НОВОЕ) ---
# --- ЛОГИКА АБОНЕМЕНТА ---
        active_membership = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False, # <--- ДОБАВЬ ЭТО! (Ищем только НЕ замороженные)
            end_date__gte=timezone.now(),
            hours_remaining__gte=hours
        ).order_by('end_date').first()

        paid_by_membership = False

        if active_membership:
            # Списываем часы
            active_membership.hours_remaining -= hours
            if active_membership.hours_remaining <= 0:
                active_membership.is_active = False
            active_membership.save()
            paid_by_membership = True

        # --- 2. РАСЧЕТ ЦЕНЫ (РАЗДЕЛЬНО) ---
        
        # А. Цена за КОРТ
        # Если есть абонемент -> цена 0. Если нет -> обычная цена.
        base_court_price = Decimal(court.price_per_hour) * hours
        final_court_price = Decimal(0) if paid_by_membership else base_court_price

        # Б. Цена за ТРЕНЕРА (всегда платим деньгами)
        final_coach_price = Decimal(0)
        if coach:
            final_coach_price = Decimal(coach.price_per_hour) * hours

        # В. Цена за УСЛУГИ (твоя старая логика)
        services_price = Decimal(0)
        services_to_create = []

        for item in services_data:
            try:
                service_obj = Service.objects.get(id=item['service_id'])
            except Service.DoesNotExist:
                raise serializers.ValidationError(f"Услуга {item['service_id']} не найдена.")

            qty = item['quantity']
            # Приводим к Decimal
            cost = Decimal(service_obj.price) * qty
            services_price += cost
            
            services_to_create.append({
                'service': service_obj,
                'quantity': qty,
                'price_at_moment': service_obj.price
            })

        # --- 3. ИТОГОВАЯ СУММА К ОПЛАТЕ ---
        total_price_money = final_court_price + final_coach_price + services_price

        # --- 🔥 4. ЛОГИКА ЛОЯЛЬНОСТИ (НОВОЕ) ---
        loyalty_discount = 0
        loyalty_info = ""
        
        # Ищем активный абонемент, у которого discount_on_court > 0
        gym_membership = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            end_date__gte=timezone.now(),
            membership_type__discount_on_court__gt=0 # Есть скидка
        ).order_by('-membership_type__discount_on_court').first() # Берем самую большую
        
        # Если нашли и оплата НЕ часами (часами скидка не нужна)
        if gym_membership and not paid_by_membership:
            percent = gym_membership.membership_type.discount_on_court
            discount_value = final_court_price * (Decimal(percent) / Decimal(100))
            
            total_price_money -= discount_value # Отнимаем от цены
            
            loyalty_discount = discount_value
            loyalty_info = f" (Loyalty {percent}%: -{discount_value}₸)"
        # --- 🔥 ЛОГИКА ПРОМОКОДА (НОВОЕ) ---
        promo_code_str = validated_data.pop('promo_code', None)
        discount_amount = Decimal(0)
        promo_description = ""

        if promo_code_str:
            try:
                # Ищем активную акцию
                promo = Promotion.objects.get(
                    promo_code__iexact=promo_code_str, # Нечувствителен к регистру
                    is_active=True,
                    start_date__lte=timezone.now(),
                    end_date__gte=timezone.now()
                )
                
                # Считаем скидку
                if promo.discount_type == 'PERCENT':
                    # Например: 10000 * 0.20 = 2000
                    discount_amount = total_price_money * (promo.discount_value / Decimal(100))
                elif promo.discount_type == 'FIXED':
                    discount_amount = promo.discount_value
                
                # Защита: скидка не может быть больше цены
                if discount_amount > total_price_money:
                    discount_amount = total_price_money
                
                # Вычитаем
                total_price_money -= discount_amount
                promo_description = f" (Промокод {promo.title}: -{discount_amount}₸)"

            except Promotion.DoesNotExist:
                # Если код не найден - просто игнорируем (или можно raise ValidationError)
                pass
        # --- 4. СОЗДАЕМ БРОНЬ ---
        booking = Booking.objects.create(
            end_time=end_time, 
            price=total_price_money, 
            **validated_data
        )
        
        # 🔥 ДОБАВЛЯЕМ ДРУЗЕЙ К БРОНИ
        if friends_ids:
            # Находим юзеров по ID и добавляем их
            friends = User.objects.filter(id__in=friends_ids)
            booking.participants.set(friends)

        # Определяем статус: 
        # Если к оплате 0 (всё покрыл абонемент) -> Сразу CONFIRMED
        # Иначе -> PENDING (ждет оплаты за тренера или услуги)
        if total_price_money == 0 and paid_by_membership:
            booking.status = 'CONFIRMED'
        else:
            booking.status = 'PENDING'
        booking.save()

        # --- 5. СОХРАНЯЕМ УСЛУГИ ---
        for svc_data in services_to_create:
            BookingService.objects.create(
                booking=booking,
                service=svc_data['service'],
                quantity=svc_data['quantity'],
                price_at_moment=svc_data['price_at_moment']
            )

        # --- 6. ТРАНЗАКЦИЯ (ОБНОВЛЕННАЯ) ---
        
        details = []
        
        # Корт: пишем, как оплачено
        if paid_by_membership:
            details.append(f"Корт {court.name} (Абонемент -{float(hours):.1f}ч)")
        else:
            details.append(f"Корт {court.name}")

        if coach: 
            details.append(f"Тренер {coach.username}")
            
        if services_to_create:
            items_list = [f"{item['service'].name} x{item['quantity']}" for item in services_to_create]
            details.append(f"Инвентарь: [{', '.join(items_list)}]")

# --- 6. ТРАНЗАКЦИЯ ---
        if total_price_money > 0:
            Transaction.objects.create(
                user=booking.user,
                booking=booking,
                amount=total_price_money,
                amount_court=final_court_price,
                amount_coach=final_coach_price,
                amount_services=services_price,
                amount_discount=discount_amount,
                transaction_type=Transaction.TransactionType.BOOKING_PAYMENT,
                payment_method=Transaction.PaymentMethod.KASPI,
                description=", ".join(details) + promo_description
            )
            
            # 👇 ДОБАВЬ ВОТ ЭТИ СТРОКИ (Фиксация оплаты)
            booking.is_paid = True
            booking.status = 'CONFIRMED'
            booking.save() 
            # 👆 ТЕПЕРЬ БРОНЬ БУДЕТ ЗЕЛЕНОЙ

        return booking


class ManagerScheduleSerializer(serializers.ModelSerializer):
    """
    Расширенный вид брони для Админа.
    Показывает контакты клиента и детали оплаты.
    """
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.CharField(source='user.phone_number', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    coach_name = serializers.CharField(source='coach.username', read_only=True, allow_null=True)
# 🔥🔥🔥 ДОБАВЛЯЕМ ВЫВОД ДРУЗЕЙ ДЛЯ АДМИНА 🔥🔥🔥
    participants = serializers.SlugRelatedField(
        many=True, 
        read_only=True, 
        slug_field='username', # Будет показывать юзернеймы/телефоны друзей
        source='participants'
    )
    class Meta:
        model = Booking
        fields = [
            'id', 
            'start_time', 
            'end_time', 
            'court_name',
            'client_name', 
            'client_phone', # 🔥 Главное для админа
            'status', 
            'is_paid', 
            'price', 
            'coach_name',
            'participants' # 👈 Не забудь добавить в список полей
        ]

    def get_client_name(self, obj):
        # Если есть Имя+Фамилия, берем их. Если нет - никнейм.
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name if full_name else obj.user.username