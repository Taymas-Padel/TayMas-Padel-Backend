from django.urls import path
from .views import (
    CheckAvailabilityView, 
    CreateBookingView, 
    UserBookingsListView, 
    CancelBookingView # <-- Добавили импорт
)

urlpatterns = [
    path('check-slots/', CheckAvailabilityView.as_view(), name='check-slots'),
    path('create/', CreateBookingView.as_view(), name='create-booking'), # <-- Новая строка
    path('my-bookings/', UserBookingsListView.as_view(), name='my-bookings'),
    path('<int:pk>/cancel/', CancelBookingView.as_view(), name='cancel-booking'),
    
]