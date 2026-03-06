# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from bookings.utils import complete_past_bookings


class Command(BaseCommand):
    help = 'Переводит прошедшие брони (end_time в прошлом) в статус COMPLETED.'

    def handle(self, *args, **options):
        count = complete_past_bookings()
        self.stdout.write(self.style.SUCCESS(f'Обновлено броней: {count}'))
