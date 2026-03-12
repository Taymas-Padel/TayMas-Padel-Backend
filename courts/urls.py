from django.urls import path
from .views import (
    CourtListAPIView,
    CourtDetailAPIView,
    CourtManageView,
    CourtManageDetailView,
    CourtGalleryUploadView,
    CourtPriceSlotsView,
)

urlpatterns = [
    path('', CourtListAPIView.as_view(), name='court-list'),
    path('<int:pk>/', CourtDetailAPIView.as_view(), name='court-detail'),
    path('manage/', CourtManageView.as_view(), name='court-manage'),
    path('manage/<int:pk>/', CourtManageDetailView.as_view(), name='court-manage-detail'),
    path('manage/<int:pk>/gallery/', CourtGalleryUploadView.as_view(), name='court-manage-gallery'),
    path('manage/<int:pk>/price-slots/', CourtPriceSlotsView.as_view(), name='court-price-slots'),
]
