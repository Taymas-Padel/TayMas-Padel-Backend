from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Court, CourtImage, CourtPriceSlot
from .serializers import CourtSerializer, CourtImageSerializer, CourtPriceSlotSerializer
from users.permissions import IsAdminRole


class CourtListAPIView(generics.ListAPIView):
    """
    GET /api/courts/ — список активных кортов.
    Параметр ?play_format=ONE_VS_ONE или TWO_VS_TWO — только корты данного формата (для лобби 1×1/2×2 и брони).
    """
    serializer_class = CourtSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Court.objects.filter(is_active=True)
        pf = self.request.query_params.get('play_format')
        if pf and pf in (Court.PlayFormat.ONE_VS_ONE, Court.PlayFormat.TWO_VS_TWO):
            qs = qs.filter(play_format=pf)
        return qs


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


class CourtGalleryUploadView(APIView):
    """
    POST /api/courts/manage/<id>/gallery/ — добавить фото в галерею корта (только ADMIN).
    Тело: multipart/form-data, поле image (файл).
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        court = get_object_or_404(Court, pk=pk)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'Поле image (файл) обязательно.'}, status=400)
        obj = CourtImage.objects.create(court=court, image=image_file)
        return Response(CourtImageSerializer(obj).data, status=201)


class CourtPriceSlotsView(APIView):
    """
    GET  /api/courts/manage/<id>/price-slots/ — список слотов корта (только ADMIN)
    POST /api/courts/manage/<id>/price-slots/ — добавить слот
    DELETE /api/courts/manage/<id>/price-slots/ — удалить все слоты корта (для пересоздания)
    """
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        court = get_object_or_404(Court, pk=pk)
        slots = court.price_slots.all().order_by('start_time')
        return Response(CourtPriceSlotSerializer(slots, many=True).data)

    def post(self, request, pk):
        court = get_object_or_404(Court, pk=pk)
        serializer = CourtPriceSlotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(court=court)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        court = get_object_or_404(Court, pk=pk)
        deleted, _ = court.price_slots.all().delete()
        return Response({'deleted': deleted})
