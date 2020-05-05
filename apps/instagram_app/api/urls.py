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
router.register('profile', ProfileViewSet)
router.register('inquiries', UserInquiryViewSet)

# router.register('packages', PackageViewSet)
# router.register('orders', OrderViewSet)
# router.register('user/packages', UserPackageViewSet)

urlpatterns += router.urls
