from django.urls import path
from rest_framework import routers

from .views import (
    InstaPageViewSet, LikedPageAPIVIEW, UserInquiryViewSet,
    UserPackageViewSet, PackageViewSet, OrderViewSet
)

urlpatterns = [
    path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),
]

router = routers.DefaultRouter()
router.register('pages', InstaPageViewSet)
router.register('packages', PackageViewSet)
router.register('user/packages', UserPackageViewSet)
router.register('orders', OrderViewSet)
router.register('inquiries', UserInquiryViewSet)

urlpatterns += router.urls
