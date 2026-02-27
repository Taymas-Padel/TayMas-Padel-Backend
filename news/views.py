from rest_framework import generics, permissions
from .models import NewsItem
from .serializers import NewsItemSerializer
from users.permissions import IsAdminRole


class NewsListView(generics.ListAPIView):
    """GET /api/news/ — список опубликованных новостей (для мобилки, открыто)."""
    serializer_class = NewsItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = NewsItem.objects.filter(is_published=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category.upper())
        return qs


class NewsDetailView(generics.RetrieveAPIView):
    """GET /api/news/<id>/ — полный текст новости."""
    queryset = NewsItem.objects.filter(is_published=True)
    serializer_class = NewsItemSerializer
    permission_classes = [permissions.AllowAny]


class NewsManageView(generics.ListCreateAPIView):
    """
    GET  /api/news/manage/ — все новости (ADMIN)
    POST /api/news/manage/ — создать новость (ADMIN)
    """
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer
    permission_classes = [IsAdminRole]


class NewsManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/news/manage/<id>/ — управление новостью (ADMIN)."""
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer
    permission_classes = [IsAdminRole]
