from rest_framework.routers import DefaultRouter
from .views import UserMembershipViewSet, MembershipTypeListView, BuyMembershipView
from django.urls import path, include

router = DefaultRouter()
router.register(r'my', UserMembershipViewSet, basename='my-memberships')

urlpatterns = [
    path('', include(router.urls)), # Теперь доступно /api/memberships/my/{id}/freeze/
    path('types/', MembershipTypeListView.as_view()),
    path('buy/<int:pk>/', BuyMembershipView.as_view()),
]