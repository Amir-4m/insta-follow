from django.urls import path
from rest_framework import routers

from .views import (
    ProfileViewSet, UserInquiryViewSet,
    OrderViewSet, CoinTransactionAPIView
)

urlpatterns = [
    path('coin-transaction/', CoinTransactionAPIView.as_view(), name='coin-transaction')
]

router = routers.DefaultRouter()
router.register('profile', ProfileViewSet, basename='profile')
router.register('inquiries', UserInquiryViewSet)
router.register('orders', OrderViewSet)

urlpatterns += router.urls
