from django.urls import path
from .views import (
    UserBookingsListView,
    UserBookingHistoryView,
    CoachScheduleView,
    CoachScheduleGridView,
    BookingDetailView,
    CreateBookingView,
    ReceptionCreateBookingView,
    CancelBookingView,
    ConfirmPaymentView,
    ClientConfirmBookingView,
    CheckAvailabilityView,
    ManagerScheduleView,
    AllBookingsView,
    AvailableCoachesView,
    BookingPricePreviewView,
)

urlpatterns = [
    # Клиент
    path('', UserBookingsListView.as_view(), name='my-bookings'),
    path('history/', UserBookingHistoryView.as_view(), name='booking-history'),
    path('coach/schedule/', CoachScheduleView.as_view(), name='coach-schedule'),
    path('coach/schedule/grid/', CoachScheduleGridView.as_view(), name='coach-schedule-grid'),
    path('<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    path('create/', CreateBookingView.as_view(), name='create-booking'),
    path('<int:pk>/cancel/', CancelBookingView.as_view(), name='cancel-booking'),
    path('<int:pk>/client-confirm/', ClientConfirmBookingView.as_view(), name='client-confirm-booking'),
    path('check-availability/', CheckAvailabilityView.as_view(), name='check-availability'),
    path('available-coaches/', AvailableCoachesView.as_view(), name='available-coaches'),
    path('price-preview/', BookingPricePreviewView.as_view(), name='price-preview'),

    # Ресепшн / CRM
    path('reception/create/', ReceptionCreateBookingView.as_view(), name='reception-create-booking'),
    path('<int:pk>/confirm-payment/', ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('manager/schedule/', ManagerScheduleView.as_view(), name='manager-schedule'),
    path('all/', AllBookingsView.as_view(), name='all-bookings'),
]
