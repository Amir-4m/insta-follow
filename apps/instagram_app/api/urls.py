from django.urls import path
from rest_framework import routers

from .views import (
    UserInquiryViewSet,
    OrderViewSet, CoinTransactionAPIView,
    InstaActionAPIView, DeviceViewSet,
    PurchaseVerificationAPIView, CoinPackageOrderViewSet,
    LoginVerification, CommentViewSet, CoinTransferAPIView,
    ReportAbuseViewSet, CoinPackageViewSet, OrderGateWayAPIView,
    GatewayAPIView, DailyRewardAPIView
)

urlpatterns = [
    path('insta-action/', InstaActionAPIView.as_view(), name='insta-action'),
    path('purchase-verification/', PurchaseVerificationAPIView.as_view(), name='purchase-verification'),
    path('login-verification/', LoginVerification.as_view(), name='login-verification'),
    path('coin-transfer/', CoinTransferAPIView.as_view(), name='coin-transfer'),
    path('order-gateway/', OrderGateWayAPIView.as_view(), name='order-gateway'),
    path('gateways/', GatewayAPIView.as_view(), name='gateways-list'),
    path('daily-reward/', DailyRewardAPIView.as_view(), name='daily-reward')

]

router = routers.DefaultRouter()
router.register('inquiries', UserInquiryViewSet)
router.register('orders', OrderViewSet)
router.register('coin-transaction', CoinTransactionAPIView)
router.register('device', DeviceViewSet)
router.register('package-order', CoinPackageOrderViewSet)
router.register('comments', CommentViewSet)
router.register('report-abuse', ReportAbuseViewSet)
router.register('coin-package', CoinPackageViewSet)

urlpatterns += router.urls
