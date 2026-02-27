from django.urls import path
from .views import ServiceListView, ServiceManageView, ServiceManageDetailView

urlpatterns = [
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('services/manage/', ServiceManageView.as_view(), name='service-manage'),
    path('services/manage/<int:pk>/', ServiceManageDetailView.as_view(), name='service-manage-detail'),
]
