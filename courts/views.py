from rest_framework import generics, permissions
from .models import Court
from .serializers import CourtSerializer

class CourtListAPIView(generics.ListCreateAPIView): # <--- БЫЛО ListAPIView, СТАЛО ListCreateAPIView
    """
    GET: Возвращает список всех кортов (доступно всем).
    POST: Создает новый корт (доступно только авторизованным).
    """
    queryset = Court.objects.filter(is_active=True)
    serializer_class = CourtSerializer
    
    # Это значит: читать могут все, а менять/создавать - только если вошел в систему
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]