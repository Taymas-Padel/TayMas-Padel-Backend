from rest_framework import generics, permissions
from .models import Service
from .serializers import ServiceSerializer
from users.permissions import IsAdminRole


class ServiceListView(generics.ListAPIView):
    """
    GET /api/inventory/services/ — список активных услуг (для выбора в брони).

    Поддерживает фильтры по query-параметрам:
    - ?group=PADEL / GYM / RECOVERY / SPORT_BAR / OTHER
    - ?category=INVENTORY / SERVICE / FOOD / DRINK / EVENT
    """
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Service.objects.filter(is_active=True)
        group = self.request.query_params.get('group')
        category = self.request.query_params.get('category')

        if group:
            qs = qs.filter(group=group.upper())
        if category:
            qs = qs.filter(category=category.upper())

        return qs.order_by('name')


class ServiceManageView(generics.ListCreateAPIView):
    """
    GET  /api/inventory/services/manage/ — все услуги включая неактивные (ADMIN)
    POST /api/inventory/services/manage/ — создать услугу (ADMIN)
    """
    queryset = Service.objects.all().order_by('group', 'category', 'name')
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminRole]


class ServiceManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/inventory/services/manage/<id>/ — управление услугой (ADMIN)."""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminRole]
