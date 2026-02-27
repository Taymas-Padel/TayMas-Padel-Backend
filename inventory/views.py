from rest_framework import generics, permissions
from .models import Service
from .serializers import ServiceSerializer
from users.permissions import IsAdminRole


class ServiceListView(generics.ListAPIView):
    """GET /api/inventory/services/ — список активных услуг (для выбора в брони)."""
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


class ServiceManageView(generics.ListCreateAPIView):
    """
    GET  /api/inventory/services/manage/ — все услуги включая неактивные (ADMIN)
    POST /api/inventory/services/manage/ — создать услугу (ADMIN)
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminRole]


class ServiceManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/inventory/services/manage/<id>/ — управление услугой (ADMIN)."""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminRole]
