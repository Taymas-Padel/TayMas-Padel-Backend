from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from django.db import transaction as db_transaction

from .models import Booking, BookingService
from django.contrib.auth import get_user_model
from inventory.models import Service
from finance.models import Transaction
from core.models import ClubSetting, ClosedDay
from core.utils import get_club_work_hours
from memberships.models import UserMembership
from decimal import Decimal
from marketing.models import Promotion
from friends.models import FriendRequest

User = get_user_model()


# ---------------------------------------------------------------------------
# Вспомогательный
# ---------------------------------------------------------------------------

class SlotAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    court_id = serializers.IntegerField(required=False)


class BookingServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = BookingService
        fields = ['service_name', 'quantity', 'price_at_moment']


# ---------------------------------------------------------------------------
# Просмотр (GET)
# ---------------------------------------------------------------------------

class BookingSerializer(serializers.ModelSerializer):
    court_name = serializers.CharField(source='court.name', read_only=True)
    coach_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    players_for_match = serializers.SerializerMethodField()
    services = BookingServiceSerializer(many=True, read_only=True)
    participants_names = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='username', source='participants'
    )
    duration_hours = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            'id', 'court', 'court_name', 'user', 'client_name', 'players_for_match',
            'start_time', 'end_time', 'duration_hours', 'price', 'status', 'is_paid',
            'coach', 'coach_name', 'services', 'participants_names',
            'membership_used', 'created_at',
        ]

    def _user_display(self, u):
        if not u:
            return None
        full = f"{u.first_name} {u.last_name}".strip()
        return full or getattr(u, 'phone_number', None) or u.username

    def get_client_name(self, obj):
        return self._user_display(obj.user)

    def get_players_for_match(self, obj):
        out = []
        if obj.user:
            out.append({"id": obj.user.id, "name": self._user_display(obj.user)})
        for p in obj.participants.all():
            out.append({"id": p.id, "name": self._user_display(p)})
        return out

    def get_coach_name(self, obj):
        if not obj.coach:
            return None
        full = f"{obj.coach.first_name} {obj.coach.last_name}".strip()
        return full or obj.coach.username


# ---------------------------------------------------------------------------
# Создание (POST)
# ---------------------------------------------------------------------------

class BookingServiceInputSerializer(serializers.Serializer):
    service_id = serializers.IntegerField(required=False)
    service = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate(self, data):
        sid = data.get('service_id') or data.get('service')
        if sid is None:
            raise serializers.ValidationError({"service_id": "Обязательное поле."})
        data['service_id'] = int(sid)
        return data


def _find_best_membership(user, hours, court=None, participant_count=1,
                          need_coach=False):
    """
    Подбирает лучший абонемент для брони.
    Приоритет: TRAINING_HOURS (если нужен тренер) > PADEL_HOURS > ничего.
    """
    base_qs = UserMembership.objects.filter(
        user=user,
        is_active=True,
        is_frozen=False,
        end_date__gte=timezone.now(),
        hours_remaining__gte=hours,
    ).select_related('membership_type').order_by('end_date')

    if need_coach:
        training = base_qs.filter(
            membership_type__service_type='TRAINING_HOURS',
            membership_type__includes_coach=True,
        )
        for m in training:
            if m.can_cover_booking(hours, court, participant_count):
                return m

    padel = base_qs.filter(
        membership_type__service_type='PADEL_HOURS',
    )
    for m in padel:
        if m.can_cover_booking(hours, court, participant_count):
            return m

    return None


class CreateBookingSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(write_only=True, min_value=30, max_value=240)
    promo_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=Transaction.PaymentMethod.choices,
        default=Transaction.PaymentMethod.KASPI,
        write_only=True,
        required=False,
    )
    coach = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=['COACH_PADEL', 'COACH_FITNESS']),
        required=False,
        allow_null=True,
    )
    services = BookingServiceInputSerializer(many=True, required=False, write_only=True)
    friends_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True,
    )
    participants_names = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='username', source='participants',
    )

    class Meta:
        model = Booking
        fields = [
            'id', 'court', 'start_time', 'duration',
            'services', 'coach', 'price', 'status',
            'promo_code', 'payment_method',
            'friends_ids', 'participants_names',
        ]
        read_only_fields = ['id', 'price', 'status']

    def validate(self, data):
        court = data['court']
        start_time = data['start_time']
        duration = data['duration']
        coach = data.get('coach')

        end_time = start_time + timedelta(minutes=duration)

        if start_time < timezone.now():
            raise serializers.ValidationError("Нельзя забронировать время в прошлом.")

        closed = ClosedDay.objects.filter(date=start_time.date()).first()
        if closed:
            raise serializers.ValidationError(
                f"В этот день клуб закрыт: {closed.reason or 'санитарный день'}."
            )

        open_h, close_h, close_at_midnight = get_club_work_hours()

        club_open = start_time.replace(hour=open_h, minute=0, second=0, microsecond=0)
        if close_at_midnight:
            # 00:00 = закрытие в полночь (конец рабочего дня = начало следующего дня 00:00)
            club_close = (start_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        else:
            club_close = start_time.replace(hour=close_h, minute=0, second=0, microsecond=0)

        close_label = "24:00 (полночь)" if close_at_midnight else f"{close_h}:00"

        if start_time < club_open:
            raise serializers.ValidationError(f"Клуб открывается в {open_h}:00.")
        if end_time > club_close:
            raise serializers.ValidationError(
                f"Игра заканчивается в {end_time.strftime('%H:%M')}, клуб закрывается в {close_label}."
            )

        if Booking.objects.filter(
            court=court,
            status__in=['CONFIRMED', 'PENDING'],
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists():
            raise serializers.ValidationError("Корт уже занят в это время.")

        if coach and Booking.objects.filter(
            coach=coach,
            status__in=['CONFIRMED', 'PENDING'],
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists():
            raise serializers.ValidationError(
                f"Тренер {coach.first_name or coach.username} уже занят."
            )

        friends_ids = data.get('friends_ids', [])
        request = self.context.get('request')
        if request:
            user = request.user
            if user.id in friends_ids:
                raise serializers.ValidationError("Не нужно добавлять себя в список участников.")
            if len(friends_ids) > 3:
                raise serializers.ValidationError("Максимум 3 участника.")

            if friends_ids:
                from django.db.models import Q as DQ
                real_friend_ids = set()
                for pair in FriendRequest.objects.filter(
                    DQ(from_user=user, status='ACCEPTED') |
                    DQ(to_user=user, status='ACCEPTED')
                ):
                    real_friend_ids.add(pair.from_user_id)
                    real_friend_ids.add(pair.to_user_id)
                real_friend_ids.discard(user.id)

                not_friends = [fid for fid in friends_ids if fid not in real_friend_ids]
                if not_friends:
                    raise serializers.ValidationError(
                        f"Пользователи с ID {not_friends} не являются вашими друзьями."
                    )

        data['_end_time'] = end_time
        return data

    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        validated_data.pop('duration')
        end_time = validated_data.pop('_end_time')
        friends_ids = validated_data.pop('friends_ids', [])
        promo_code_str = validated_data.pop('promo_code', None)
        payment_method = validated_data.pop('payment_method', Transaction.PaymentMethod.KASPI)

        court = validated_data['court']
        coach = validated_data.get('coach')
        user = validated_data['user']

        hours = Decimal(str((end_time - validated_data['start_time']).total_seconds() / 3600))
        participant_count = 1 + len(friends_ids)

        # --- 1. Подбор абонемента ---
        active_membership = _find_best_membership(
            user=user,
            hours=hours,
            court=court,
            participant_count=participant_count,
            need_coach=bool(coach),
        )

        paid_by_membership = bool(active_membership)
        coach_covered = False
        prime_surcharge = Decimal('0')
        prime_hours = Decimal('0')

        if active_membership:
            active_membership.hours_remaining -= hours
            if active_membership.hours_remaining <= 0:
                active_membership.is_active = False
            active_membership.save()

            mt = active_membership.membership_type

            if mt.includes_coach and coach:
                coach_covered = True

            prime_surcharge, prime_hours = mt.calc_prime_surcharge(
                validated_data['start_time'], end_time,
            )

        # --- 2. Расчёт цены ---
        base_court_price = Decimal(str(court.price_per_hour)) * hours
        final_court_price = Decimal('0') if paid_by_membership else base_court_price

        final_coach_price = Decimal('0')
        if coach and not coach_covered:
            final_coach_price = Decimal(str(coach.price_per_hour)) * hours

        services_price = Decimal('0')
        services_to_create = []
        for item in services_data:
            try:
                svc = Service.objects.get(id=item['service_id'], is_active=True)
            except Service.DoesNotExist:
                raise serializers.ValidationError(f"Услуга ID={item['service_id']} не найдена.")
            qty = item['quantity']
            cost = Decimal(str(svc.price)) * qty
            services_price += cost
            services_to_create.append({
                'service': svc, 'quantity': qty, 'price_at_moment': svc.price,
            })

        total_price = final_court_price + final_coach_price + services_price + prime_surcharge

        # --- 3. Лояльность (скидка через абонемент) ---
        discount_loyalty = Decimal('0')
        if not paid_by_membership and final_court_price > 0:
            gym_mem = UserMembership.objects.filter(
                user=user,
                is_active=True,
                is_frozen=False,
                end_date__gte=timezone.now(),
                membership_type__discount_on_court__gt=0,
            ).order_by('-membership_type__discount_on_court').first()
            if gym_mem:
                pct = gym_mem.membership_type.discount_on_court
                discount_loyalty = final_court_price * (Decimal(str(pct)) / Decimal('100'))
                total_price -= discount_loyalty

        # --- 4. Промокод ---
        discount_promo = Decimal('0')
        promo_title = ''
        if promo_code_str:
            try:
                promo = Promotion.objects.get(
                    promo_code__iexact=promo_code_str,
                    is_active=True,
                    start_date__lte=timezone.now(),
                    end_date__gte=timezone.now(),
                )
                if promo.discount_type == 'PERCENT':
                    discount_promo = total_price * (promo.discount_value / Decimal('100'))
                else:
                    discount_promo = promo.discount_value
                discount_promo = min(discount_promo, total_price)
                total_price -= discount_promo
                promo_title = promo.title
            except Promotion.DoesNotExist:
                pass

        total_discount = discount_loyalty + discount_promo

        # --- 5. Создаём бронь ---
        initial_status = 'CONFIRMED' if (total_price == 0 and paid_by_membership) else 'PENDING'

        with db_transaction.atomic():
            booking = Booking.objects.create(
                end_time=end_time,
                price=total_price,
                status=initial_status,
                is_paid=False,
                membership_used=active_membership if paid_by_membership else None,
                **validated_data,
            )

            if friends_ids:
                booking.participants.set(User.objects.filter(id__in=friends_ids))

            for svc_data in services_to_create:
                BookingService.objects.create(
                    booking=booking,
                    service=svc_data['service'],
                    quantity=svc_data['quantity'],
                    price_at_moment=svc_data['price_at_moment'],
                )

            if total_price > 0:
                desc_parts = []
                if paid_by_membership:
                    mem_name = active_membership.membership_type.name
                    desc_parts.append(
                        f"Корт {court.name} (абонемент «{mem_name}», -{float(hours):.1f}ч)"
                    )
                    if prime_surcharge > 0:
                        desc_parts.append(
                            f"Доплата прайм-тайм: {prime_surcharge}₸ ({float(prime_hours):.1f}ч)"
                        )
                else:
                    desc_parts.append(f"Корт {court.name}")
                if coach:
                    if coach_covered:
                        desc_parts.append(f"Тренер: {coach.first_name or coach.username} (по абонементу)")
                    else:
                        desc_parts.append(f"Тренер: {coach.first_name or coach.username}")
                if services_to_create:
                    items = [f"{s['service'].name}×{s['quantity']}" for s in services_to_create]
                    desc_parts.append(f"Инвентарь: {', '.join(items)}")
                if promo_title:
                    desc_parts.append(f"Промокод «{promo_title}»: -{discount_promo}₸")

                Transaction.objects.create(
                    user=user,
                    booking=booking,
                    amount=total_price,
                    amount_court=final_court_price,
                    amount_coach=final_coach_price,
                    amount_services=services_price,
                    amount_discount=total_discount,
                    transaction_type=Transaction.TransactionType.BOOKING_PAYMENT,
                    payment_method=payment_method,
                    description=', '.join(desc_parts),
                )

                booking.status = 'CONFIRMED'
                booking.is_paid = True
                booking.save(update_fields=['status', 'is_paid'])

        return booking


# ---------------------------------------------------------------------------
# Сериализатор для расписания менеджера/ресепшн
# ---------------------------------------------------------------------------

class ManagerScheduleSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.CharField(source='user.phone_number', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    coach_name = serializers.SerializerMethodField()
    participants = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username')
    services = BookingServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'start_time', 'end_time', 'court_name',
            'client_name', 'client_phone', 'status', 'is_paid',
            'price', 'coach_name', 'participants', 'services',
        ]

    def get_client_name(self, obj):
        full = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full or obj.user.username

    def get_coach_name(self, obj):
        if not obj.coach:
            return None
        full = f"{obj.coach.first_name} {obj.coach.last_name}".strip()
        return full or obj.coach.username
