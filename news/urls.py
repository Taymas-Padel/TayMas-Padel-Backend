from django.urls import path
from .views import NewsListView, NewsDetailView, NewsManageView, NewsManageDetailView

urlpatterns = [
    path('', NewsListView.as_view(), name='news-list'),
    path('<int:pk>/', NewsDetailView.as_view(), name='news-detail'),
    path('manage/', NewsManageView.as_view(), name='news-manage'),
    path('manage/<int:pk>/', NewsManageDetailView.as_view(), name='news-manage-detail'),
]
