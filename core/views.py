from datetime import datetime as dt
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import ClubSetting, ClosedDay
from .serializers import ClubSettingSerializer, ClosedDaySerializer


class ClubSettingListView(ListAPIView):
    """
    GET /api/core/settings/
    Список настроек клуба (время работы, отмена). Доступно всем.
    """
    queryset = ClubSetting.objects.all()
    serializer_class = ClubSettingSerializer
    permission_classes = [AllowAny]


class ClosedDaysListView(APIView):
    """
    GET /api/core/closed-days/?from=YYYY-MM-DD&to=YYYY-MM-DD
    Выходные и праздничные дни для календаря. Без параметров — с сегодня по +1 год.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        today = timezone.now().date()
        if from_date:
            try:
                start = dt.strptime(from_date, '%Y-%m-%d').date()
            except ValueError:
                start = today
        else:
            start = today
        if to_date:
            try:
                end = dt.strptime(to_date, '%Y-%m-%d').date()
            except ValueError:
                end = start.replace(year=start.year + 1)
        else:
            end = start.replace(year=start.year + 1)
        if start > end:
            start, end = end, start
        qs = ClosedDay.objects.filter(date__gte=start, date__lte=end).order_by('date')
        return Response(ClosedDaySerializer(qs, many=True).data)