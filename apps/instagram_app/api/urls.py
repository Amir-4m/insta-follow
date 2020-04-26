from django.urls import path
from rest_framework import routers

from .views import (
    InstaPageViewSet, LikedPageAPIVIEW, UserInquiryLikeAPIView,
    UserPackageViewSet, PackageViewSet, OrderViewSet
)

urlpatterns = [
    path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),
    path('inquiries/like/', UserInquiryLikeAPIView.as_view(), name="user-inquiries-like"),
]

router = routers.DefaultRouter()
router.register('pages', InstaPageViewSet)
router.register('packages', PackageViewSet)
router.register('user/packages', UserPackageViewSet)
router.register('orders', OrderViewSet)

urlpatterns += router.urls
