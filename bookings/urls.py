from django.urls import path
from .views import (
    UserBookingsListView, 
    CreateBookingView, 
    CancelBookingView, 
    CheckAvailabilityView
)

urlpatterns = [
    # GET: получить список моих броней
    path('', UserBookingsListView.as_view(), name='my-bookings'),
    # POST: создать бронь
    path('create/', CreateBookingView.as_view(), name='create-booking'),
    # POST: отменить бронь по ID
    path('<int:pk>/cancel/', CancelBookingView.as_view(), name='cancel-booking'),
    # GET: проверить свободное время (?court_id=1&date=2025-12-20)
    path('check-availability/', CheckAvailabilityView.as_view(), name='check-availability'),
]