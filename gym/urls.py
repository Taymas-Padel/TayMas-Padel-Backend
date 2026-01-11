from django.urls import path
from .views import GymCheckInView, GenerateQREntryView, ScanQREntryView
urlpatterns = [
    path('checkin/', GymCheckInView.as_view(), name='gym-checkin'),
    path('qr/generate/', GenerateQREntryView.as_view(), name='qr-generate'),
    
    # 2. Ссылка для Админа/Турникета (проверить чужой QR)
    path('qr/scan/', ScanQREntryView.as_view(), name='qr-scan'),
]