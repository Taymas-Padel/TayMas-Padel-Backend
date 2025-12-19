from django.urls import path
from .views import MembershipTypeListView, BuyMembershipView

urlpatterns = [
    path('types/', MembershipTypeListView.as_view(), name='membership-list'),
    path('buy/<int:pk>/', BuyMembershipView.as_view(), name='membership-buy'),
]