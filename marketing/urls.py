from django.urls import path
from .views import ActivePromotionsView, PromotionManageView, PromotionManageDetailView, ValidatePromoView

urlpatterns = [
    path('promos/', ActivePromotionsView.as_view(), name='active-promos'),
    path('validate-promo/', ValidatePromoView.as_view(), name='validate-promo'),
    path('manage/', PromotionManageView.as_view(), name='promo-manage'),
    path('manage/<int:pk>/', PromotionManageDetailView.as_view(), name='promo-manage-detail'),
]