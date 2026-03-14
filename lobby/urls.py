from django.urls import path
from .views import (
    LobbyListCreateView,
    LobbyListFormatRedirectView,
    LobbyDetailView,
    LobbyJoinView,
    LobbyLeaveView,
    LobbyAssignTeamsView,
    LobbyBookView,
    LobbyMyExtrasView,
    LobbyPayShareView,
    LobbyPaymentStatusView,
    MyLobbiesView,
    LobbyCloseView,
    LobbyProposeTimeView,
    LobbyVoteProposalView,
    LobbyAcceptProposalView,
)

urlpatterns = [
    path('', LobbyListCreateView.as_view(), name='lobby-list-create'),
    path('my/', MyLobbiesView.as_view(), name='my-lobbies'),
    path('<int:pk>/', LobbyDetailView.as_view(), name='lobby-detail'),
    path('<int:pk>/join/', LobbyJoinView.as_view(), name='lobby-join'),
    path('<int:pk>/leave/', LobbyLeaveView.as_view(), name='lobby-leave'),
    path('<int:pk>/close/', LobbyCloseView.as_view(), name='lobby-close'),

    # Согласование времени/корта
    path('<int:pk>/proposals/', LobbyProposeTimeView.as_view(), name='lobby-proposals'),
    path('<int:pk>/proposals/<int:proposal_id>/vote/', LobbyVoteProposalView.as_view(), name='lobby-vote'),
    path('<int:pk>/proposals/<int:proposal_id>/accept/', LobbyAcceptProposalView.as_view(), name='lobby-accept'),

    # Команды и бронь
    path('<int:pk>/assign-teams/', LobbyAssignTeamsView.as_view(), name='lobby-assign-teams'),
    path('<int:pk>/book/', LobbyBookView.as_view(), name='lobby-book'),

    # Личные услуги и оплата
    path('<int:pk>/my-extras/', LobbyMyExtrasView.as_view(), name='lobby-my-extras'),
    path('<int:pk>/my-extras/<int:extra_id>/', LobbyMyExtrasView.as_view(), name='lobby-my-extras-delete'),
    path('<int:pk>/pay-share/', LobbyPayShareView.as_view(), name='lobby-pay-share'),
    path('<int:pk>/payment-status/', LobbyPaymentStatusView.as_view(), name='lobby-payment-status'),
    # Если клиент ошибочно отправил формат в path (напр. /api/lobby/SINGLE/) — редирект на список с ?format=
    path('<str:fmt>/', LobbyListFormatRedirectView.as_view(), name='lobby-list-format-redirect'),
]
