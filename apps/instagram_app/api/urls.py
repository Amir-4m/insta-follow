from django.urls import path
from rest_framework import routers

from .views import (
    ProfileViewSet, UserInquiryViewSet,
    OrderViewSet, CoinTransactionAPIView,
    InstaActionAPIView, DeviceViewSet,
    PurchaseVerificationAPIView, CoinPackageOrderViewSet
)

urlpatterns = [
    path('insta-action/', InstaActionAPIView.as_view(), name='insta-action'),
    path('purchase-verification/', PurchaseVerificationAPIView.as_view(), name='purchase-verification')

]

router = routers.DefaultRouter()
router.register('profile', ProfileViewSet, basename='profile')
router.register('inquiries', UserInquiryViewSet)
router.register('orders', OrderViewSet)
router.register('coin-transaction', CoinTransactionAPIView)
router.register('device', DeviceViewSet)
router.register('package-order', CoinPackageOrderViewSet)

urlpatterns += router.urls
