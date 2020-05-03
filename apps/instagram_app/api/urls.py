from django.urls import path
from rest_framework import routers

from .views import (
    InstaPageViewSet, LikedPageAPIVIEW, UserInquiryViewSet,
    UserPackageViewSet, PackageViewSet, OrderViewSet, CoinTransactionAPIView
)

urlpatterns = [
    # path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),
    path('coin-transaction/', CoinTransactionAPIView.as_view(), name='coin-transaction')
]

router = routers.DefaultRouter()
router.register('pages', InstaPageViewSet)
router.register('inquiries', UserInquiryViewSet)

# router.register('packages', PackageViewSet)
# router.register('orders', OrderViewSet)
# router.register('user/packages', UserPackageViewSet)

urlpatterns += router.urls
