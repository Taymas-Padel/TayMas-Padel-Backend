from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from bookings.models import Booking
from courts.models import Court
# Импортируем нашу единую таблицу транзакций
from finance.models import Transaction

class DirectorDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # --- 1. ФИНАНСЫ (Уже есть) ---
        total_revenue = Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0
        month_revenue = Transaction.objects.filter(created_at__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
        today_revenue = Transaction.objects.filter(created_at__gte=today_start).aggregate(total=Sum('amount'))['total'] or 0

        # --- 2. СТРУКТУРА (Уже есть) ---
        revenue_structure = Transaction.objects.values('transaction_type').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        structure_data = [
            {
                "type": item['transaction_type'],
                "label": dict(Transaction.TransactionType.choices).get(item['transaction_type']),
                "amount": item['total_amount'],
                "count": item['count']
            } 
            for item in revenue_structure
        ]

        # --- 🔥 3. ЗАГРУЗКА (НОВОЕ) ---
        # Считаем, сколько часов забронировано сегодня (исключая отмены)
# --- 🔥 3. ЗАГРУЗКА (ИСПРАВЛЕНИЕ) ---
        bookings_today = Booking.objects.filter(
            start_time__gte=today_start,
            start_time__lt=today_end,
            status__in=['CONFIRMED', 'PENDING']
        )
        
        # Считаем минуты вручную (Конец - Начало)
        booked_minutes = 0
        for b in bookings_today:
            # Вычисляем разницу во времени
            delta = b.end_time - b.start_time
            # Превращаем в минуты
            booked_minutes += (delta.total_seconds() / 60)
        
        # Считаем Максимальную емкость
        total_courts = Court.objects.count()
        WORK_MINUTES_PER_DAY = 15 * 60  # 15 рабочих часов * 60 минут
        
        max_capacity_minutes = total_courts * WORK_MINUTES_PER_DAY
        
        occupancy_rate = 0
        if max_capacity_minutes > 0:
            occupancy_rate = round((booked_minutes / max_capacity_minutes) * 100, 1)

        return Response({
            "period": {
                "date": now.date(),
                "month": now.strftime('%B')
            },
            "kpi": {
                "today": today_revenue,
                "this_month": month_revenue,
                "total_all_time": total_revenue,
                "occupancy_rate_today": f"{occupancy_rate}%" # 👈 НОВАЯ ЦИФРА
            },
            "revenue_structure": structure_data
        })
