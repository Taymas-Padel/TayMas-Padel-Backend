from django.urls import path
from .views import (
    ConversationListView,
    StartConversationView,
    MessageListView,
    SendMessageView,
    MarkReadView,
    UnreadCountView,
)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/start/', StartConversationView.as_view(), name='start-conversation'),
    path('conversations/<int:conv_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<int:conv_id>/send/', SendMessageView.as_view(), name='send-message'),
    path('conversations/<int:conv_id>/read/', MarkReadView.as_view(), name='mark-read'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
]
