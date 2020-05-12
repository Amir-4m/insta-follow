from django.urls import path
from rest_framework import routers

from .views import (
    ProfileViewSet, UserInquiryViewSet,
    OrderViewSet, CoinTransactionAPIView,
    InstaActionAPIView, DeviceViewSet
)

urlpatterns = [
    path('insta-action/', InstaActionAPIView.as_view(), name='insta-action')

]

router = routers.DefaultRouter()
router.register('profile', ProfileViewSet, basename='profile')
router.register('inquiries', UserInquiryViewSet)
router.register('orders', OrderViewSet)
router.register('coin-transaction', CoinTransactionAPIView)
router.register('device', DeviceViewSet)

urlpatterns += router.urls
