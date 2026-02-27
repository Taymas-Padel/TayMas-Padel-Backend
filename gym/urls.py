from django.urls import path
from .views import (
    GymCheckInView,
    GenerateQREntryView,
    ScanQREntryView,
    PersonalTrainingListCreateView,
    PersonalTrainingDetailView,
    MyGymVisitsView,
)

urlpatterns = [
    path('checkin/', GymCheckInView.as_view(), name='gym-checkin'),
    path('visits/', MyGymVisitsView.as_view(), name='my-gym-visits'),
    path('qr/generate/', GenerateQREntryView.as_view(), name='qr-generate'),
    path('qr/scan/', ScanQREntryView.as_view(), name='qr-scan'),
    path('personal-training/', PersonalTrainingListCreateView.as_view(), name='personal-training-list'),
    path('personal-training/<int:pk>/', PersonalTrainingDetailView.as_view(), name='personal-training-detail'),
]
