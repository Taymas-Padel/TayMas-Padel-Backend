from datetime import datetime as dt
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import status
from django.utils import timezone
from .models import ClubSetting, ClosedDay
from .serializers import ClubSettingSerializer, ClosedDaySerializer


class ClubSettingListView(ListAPIView):
    """
    GET /api/core/settings/
    Список настроек клуба (время работы, политика отмены и т.д.).
    """
    queryset = ClubSetting.objects.all()
    serializer_class = ClubSettingSerializer
    permission_classes = [AllowAny]


class ClubSettingDetailView(RetrieveUpdateAPIView):
    """
    GET   /api/core/settings/<key>/
    PATCH /api/core/settings/<key>/
    """
    queryset = ClubSetting.objects.all()
    serializer_class = ClubSettingSerializer
    lookup_field = 'key'
    lookup_url_kwarg = 'key'

    def get_permissions(self):
        # Читать может любой, менять — только staff/админ
        if self.request.method in ('PATCH', 'PUT'):
            return [IsAdminUser()]
        return [AllowAny()]


class ClosedDaysListView(APIView):
    """
    GET  /api/core/closed-days/?from=YYYY-MM-DD&to=YYYY-MM-DD
    POST /api/core/closed-days/ — создать выходной (date, reason). Только для staff.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [AllowAny()]

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

    def post(self, request):
        ser = ClosedDaySerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)