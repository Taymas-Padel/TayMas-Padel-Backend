from django.urls import path
from .views import ActivePromotionsView

urlpatterns = [
    path('promos/', ActivePromotionsView.as_view(), name='active-promos'),
]