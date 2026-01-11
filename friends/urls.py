from django.urls import path
from .views import SendFriendRequestView, IncomingRequestsView, ManageRequestView, MyFriendsListView

urlpatterns = [
    path('send/', SendFriendRequestView.as_view(), name='send-request'),
    path('incoming/', IncomingRequestsView.as_view(), name='incoming-requests'),
    path('manage/<int:pk>/', ManageRequestView.as_view(), name='manage-request'), # accept/reject
    path('list/', MyFriendsListView.as_view(), name='my-friends'), # Список друзей
]