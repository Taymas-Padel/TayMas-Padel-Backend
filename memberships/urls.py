from rest_framework.routers import DefaultRouter
from .views import (
    UserMembershipViewSet,
    MembershipTypeListView,
    MembershipTypeManageView,
    MembershipTypeManageDetailView,
    BuyMembershipView,
    ReceptionBuyMembershipView,
    AllMembershipsView,
)
from django.urls import path, include

router = DefaultRouter()
router.register(r'my', UserMembershipViewSet, basename='my-memberships')

urlpatterns = [
    path('', include(router.urls)),
    path('types/', MembershipTypeListView.as_view()),
    path('types/manage/', MembershipTypeManageView.as_view(), name='membership-types-manage'),
    path('types/manage/<int:pk>/', MembershipTypeManageDetailView.as_view(), name='membership-type-manage-detail'),
    path('buy/<int:pk>/', BuyMembershipView.as_view()),
    path('reception/buy/', ReceptionBuyMembershipView.as_view(), name='reception-buy-membership'),
    path('all/', AllMembershipsView.as_view(), name='all-memberships'),
]