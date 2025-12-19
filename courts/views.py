from rest_framework import generics, permissions
from .models import Court
from .serializers import CourtSerializer

class CourtListAPIView(generics.ListCreateAPIView):
    """
    GET: Возвращает список активных кортов (доступно всем).
    POST: Создает новый корт (доступно только авторизованным).
    """
    # Показываем только активные корты (не на ремонте)
    queryset = Court.objects.filter(is_active=True)
    serializer_class = CourtSerializer
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]