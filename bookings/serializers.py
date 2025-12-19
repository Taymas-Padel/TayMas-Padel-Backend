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

    class Meta:
        model = Booking
        fields = ['id', 'court', 'court_name', 'start_time', 'end_time', 'price', 'status', 'coach', 'coach_name', 'services']


# --- 3. Сериализаторы для СОЗДАНИЯ (POST) ---

class BookingServiceInputSerializer(serializers.Serializer):
    """Вспомогательный для приема списка услуг при создании"""
    service_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)

class CreateBookingSerializer(serializers.ModelSerializer):
    """Сложный сериализатор для создания брони с расчетами"""
    duration = serializers.IntegerField(write_only=True)
    
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='COACH_PADEL'),
        required=False, 
        allow_null=True
    )
    
    # Принимаем список услуг
    services = BookingServiceInputSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'court', 'start_time', 'duration', 'coach', 'services', 'price', 'end_time', 'status']
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
        
        court = validated_data['court']
        coach = validated_data.get('coach')
        user = validated_data['user'] # Нам нужен юзер для поиска абонемента

        # --- 0. ПОДГОТОВКА (Часы) ---
        # Используем Decimal для точности (чтобы не было 9.99999 часов)
        hours = Decimal(duration) / Decimal(60)

        # --- 🔥 1. ЛОГИКА АБОНЕМЕНТА (НОВОЕ) ---
        # Ищем активный пакет, где хватает часов
        active_membership = UserMembership.objects.filter(
            user=user,
            is_active=True,
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

        # --- 4. СОЗДАЕМ БРОНЬ ---
        booking = Booking.objects.create(
            end_time=end_time, 
            price=total_price_money, 
            **validated_data
        )

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

        Transaction.objects.create(
            user=booking.user,
            booking=booking,
            
            # Общая сумма ДЕНЕГ
            amount=total_price_money,
            
            # Детализация (Четко раскладываем по полкам)
            amount_court=final_court_price,
            amount_coach=final_coach_price,
            amount_services=services_price,
            
            transaction_type='PAYMENT',
            description=", ".join(details)
        )
        
        return booking

