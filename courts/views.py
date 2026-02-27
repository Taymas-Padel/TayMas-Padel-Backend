from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Court
from .serializers import CourtSerializer
from users.permissions import IsAdminRole


class CourtListAPIView(generics.ListAPIView):
    """
    GET /api/courts/ — список активных кортов (доступно всем).
    """
    queryset = Court.objects.filter(is_active=True)
    serializer_class = CourtSerializer
    permission_classes = [permissions.AllowAny]


class CourtDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/courts/<id>/ — детальная карточка корта.
    """
    queryset = Court.objects.filter(is_active=True)
    serializer_class = CourtSerializer
    permission_classes = [permissions.AllowAny]


class CourtManageView(generics.ListCreateAPIView):
    """
    GET  /api/courts/manage/ — все корты включая неактивные (только ADMIN)
    POST /api/courts/manage/ — создать корт (только ADMIN)
    """
    queryset = Court.objects.all()
    serializer_class = CourtSerializer
    permission_classes = [IsAdminRole]


class CourtManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/courts/manage/<id>/ — управление кортом (только ADMIN)
    """
    queryset = Court.objects.all()
    serializer_class = CourtSerializer
    permission_classes = [IsAdminRole]
