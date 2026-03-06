# -*- coding: utf-8 -*-
from django.utils import timezone
from .models import Booking


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
