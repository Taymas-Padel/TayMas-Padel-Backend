from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta

from bookings.models import Booking
from courts.models import Court
from finance.models import Transaction
from users.permissions import IsReceptionist, IsAdminRole
from core.models import ClubSetting


class DirectorDashboardView(APIView):
    """
    GET /api/analytics/dashboard/
    Расширенный дашборд для ADMIN (финансы, загрузка, активность).
    """
    permission_classes = [IsAdminRole]  # ИСПРАВЛЕНО: было IsAdminUser (только суперюзеры)

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        # --- 1. Финансы ---
        total_revenue = Transaction.objects.filter(
            amount__gt=0
        ).aggregate(t=Sum('amount'))['t'] or 0

        month_revenue = Transaction.objects.filter(
            created_at__gte=month_start, amount__gt=0
        ).aggregate(t=Sum('amount'))['t'] or 0

        today_revenue = Transaction.objects.filter(
            created_at__gte=today_start, created_at__lte=today_end, amount__gt=0
        ).aggregate(t=Sum('amount'))['t'] or 0

        week_revenue = Transaction.objects.filter(
            created_at__gte=week_start, amount__gt=0
        ).aggregate(t=Sum('amount'))['t'] or 0

        # --- 2. Структура выручки по типам ---
        revenue_structure = []
        for t_code, t_label in Transaction.TransactionType.choices:
            val = Transaction.objects.filter(
                transaction_type=t_code, amount__gt=0
            ).aggregate(t=Sum('amount'))['t'] or 0
            cnt = Transaction.objects.filter(
                transaction_type=t_code, amount__gt=0
            ).count()
            if val > 0:
                revenue_structure.append({
                    "type": t_code,
                    "label": t_label,
                    "amount": float(val),
                    "count": cnt,
                })

        # --- 3. Загрузка кортов сегодня ---
        # ИСПРАВЛЕНО: берём рабочее время из ClubSetting
        open_s = ClubSetting.objects.filter(key='OPEN_TIME').first()
        close_s = ClubSetting.objects.filter(key='CLOSE_TIME').first()
        open_h = int(open_s.value.split(':')[0]) if open_s else 7
        close_h = int(close_s.value.split(':')[0]) if close_s else 23
        work_minutes_per_day = (close_h - open_h) * 60

        bookings_today = Booking.objects.filter(
            start_time__gte=today_start,
            start_time__lte=today_end,
            status__in=['CONFIRMED', 'PENDING'],
        )

        booked_minutes = 0
        for b in bookings_today:
            booked_minutes += (b.end_time - b.start_time).total_seconds() / 60

        total_courts = Court.objects.filter(is_active=True).count()
        max_capacity = total_courts * work_minutes_per_day
        occupancy = round((booked_minutes / max_capacity) * 100, 1) if max_capacity > 0 else 0

        # --- 4. Брони сегодня по статусам ---
        bookings_today_count = Booking.objects.filter(
            start_time__date=now.date()
        ).exclude(status='CANCELED').count()

        pending_count = Booking.objects.filter(
            status='PENDING', start_time__gte=today_start
        ).count()

        # --- 5. Активность за неделю ---
        week_bookings = Booking.objects.filter(
            created_at__gte=week_start
        ).exclude(status='CANCELED').count()

        # --- 6. Кол-во клиентов ---
        from django.contrib.auth import get_user_model
        User = get_user_model()
        total_clients = User.objects.filter(role='CLIENT').count()
        new_clients_month = User.objects.filter(
            role='CLIENT', created_at__gte=month_start
        ).count()

        return Response({
            "period": {
                "date": now.date(),
                "month": now.strftime('%B %Y'),
            },
            "kpi": {
                "today_revenue": float(today_revenue),
                "week_revenue": float(week_revenue),
                "month_revenue": float(month_revenue),
                "total_revenue": float(total_revenue),
                "occupancy_rate_today": f"{occupancy}%",
                "bookings_today": bookings_today_count,
                "pending_payments": pending_count,
                "week_bookings": week_bookings,
                "total_clients": total_clients,
                "new_clients_this_month": new_clients_month,
            },
            "revenue_structure": revenue_structure,
            "work_hours": f"{open_h}:00 – {close_h}:00",
        })


class ReceptionDashboardView(APIView):
    """
    GET /api/analytics/reception/
    Упрощённый дашборд для ресепшн (только сегодняшние данные).
    """
    permission_classes = [IsReceptionist]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59)

        # Брони сегодня
        bookings_today = Booking.objects.filter(
            start_time__gte=today_start,
            start_time__lte=today_end,
        ).exclude(status='CANCELED')

        # Ожидают оплаты
        pending = bookings_today.filter(status='PENDING', is_paid=False).count()

        # Выручка сегодня
        today_revenue = Transaction.objects.filter(
            created_at__gte=today_start, amount__gt=0
        ).aggregate(t=Sum('amount'))['t'] or 0

        # Ближайшие брони (следующие 3 часа)
        in_3h = now + timedelta(hours=3)
        upcoming = Booking.objects.filter(
            start_time__gte=now,
            start_time__lte=in_3h,
            status__in=['CONFIRMED', 'PENDING'],
        ).select_related('user', 'court').order_by('start_time')[:10]

        upcoming_data = []
        for b in upcoming:
            upcoming_data.append({
                "id": b.id,
                "court": b.court.name,
                "start_time": timezone.localtime(b.start_time).strftime('%H:%M'),
                "client": f"{b.user.first_name} {b.user.last_name}".strip() or b.user.phone_number,
                "status": b.status,
                "is_paid": b.is_paid,
                "price": float(b.price),
            })

        return Response({
            "today": now.date().strftime('%d.%m.%Y'),
            "bookings_today": bookings_today.count(),
            "pending_payments": pending,
            "today_revenue": float(today_revenue),
            "upcoming_bookings": upcoming_data,
        })
