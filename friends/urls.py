from django.urls import path
from .views import (
    SendFriendRequestView,
    IncomingRequestsView,
    OutgoingRequestsView,
    RespondToRequestView,
    CancelFriendRequestView,
    RemoveFriendView,
    FriendListView,
)

urlpatterns = [
    path('', FriendListView.as_view(), name='friend-list'),
    path('send/', SendFriendRequestView.as_view(), name='send-request'),
    path('requests/', IncomingRequestsView.as_view(), name='incoming-requests'),
    path('requests/outgoing/', OutgoingRequestsView.as_view(), name='outgoing-requests'),
    path('respond/', RespondToRequestView.as_view(), name='respond-request'),
    path('cancel/', CancelFriendRequestView.as_view(), name='cancel-request'),
    path('remove/', RemoveFriendView.as_view(), name='remove-friend'),
]