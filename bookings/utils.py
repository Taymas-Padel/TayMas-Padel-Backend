# -*- coding: utf-8 -*-
from django.utils import timezone
from decimal import Decimal

from .models import Booking
from memberships.models import UserMembership


def find_best_membership(user, hours, court=None, participant_count=1, need_coach=False):
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


def compute_participant_share(
    user,
    court,
    start_time,
    end_time,
    coach=None,
    court_total=None,
    coach_total=None,
    share_n=1,
):
    """
    Считает долю одного участника за слот (корт + тренер + абонемент + прайм + скидка).
    Списание часов абонемента не выполняет — это делает вызывающий код.

    Возвращает dict: court_share, coach_share, prime_surcharge, total,
    membership_used, membership (UserMembership | None).
    """
    hours = Decimal(str((end_time - start_time).total_seconds() / 3600))
    if court_total is None:
        court_total = court.get_price_for_slot(start_time, end_time)
    else:
        court_total = Decimal(str(court_total))
    if coach_total is None:
        if coach:
            coach_total = Decimal(str(coach.get_coach_price_per_hour(share_n))) * hours
        else:
            coach_total = Decimal('0')
    else:
        coach_total = Decimal(str(coach_total))

    share_n = max(1, int(share_n))
    court_share_base = (court_total / share_n).quantize(Decimal('0.01'))
    coach_share_base = (coach_total / share_n).quantize(Decimal('0.01'))

    active_membership = find_best_membership(
        user=user,
        hours=hours,
        court=court,
        participant_count=1,
        need_coach=bool(coach),
    )

    membership_used = bool(active_membership)
    court_share = Decimal('0')
    coach_share = coach_share_base
    prime_surcharge = Decimal('0')

    prime_hours = Decimal('0')
    if active_membership:
        mt = active_membership.membership_type
        court_share = Decimal('0')
        if mt.includes_coach and coach:
            coach_share = Decimal('0')
        else:
            coach_share = coach_share_base
        prime_surcharge, prime_hours = mt.calc_prime_surcharge(start_time, end_time)
        prime_surcharge = prime_surcharge.quantize(Decimal('0.01'))
    discount_court = Decimal('0')
    if not active_membership:
        court_share = court_share_base
        # Скидка по абонементу (discount_on_court)
        gym_mem = UserMembership.objects.filter(
            user=user,
            is_active=True,
            is_frozen=False,
            end_date__gte=timezone.now(),
            membership_type__discount_on_court__gt=0,
        ).order_by('-membership_type__discount_on_court').first()
        if gym_mem:
            pct = gym_mem.membership_type.discount_on_court
            discount_court = (court_share * (Decimal(str(pct)) / Decimal('100'))).quantize(Decimal('0.01'))
            court_share = court_share - discount_court

    total = (court_share + coach_share + prime_surcharge).quantize(Decimal('0.01'))
    return {
        'court_share': court_share,
        'coach_share': coach_share,
        'prime_surcharge': prime_surcharge,
        'prime_hours': prime_hours,
        'total': total,
        'membership_used': membership_used,
        'membership': active_membership,
        'hours': hours,
        'discount_court': discount_court,
    }


def complete_past_bookings():
    """
    Переводит в статус COMPLETED все брони, у которых end_time уже прошёл
    и статус ещё CONFIRMED или PENDING. Возвращает количество обновлённых записей.
    """
    now = timezone.now()
    updated = Booking.objects.filter(
        end_time__lt=now,
        status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING],
    ).update(status=Booking.Status.COMPLETED)
    return updated
