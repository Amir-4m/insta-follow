from django.urls import path
from rest_framework import routers

from .views import InstaPageViewSet, LikedPageAPIVIEW, UserInquiryLikeAPIView

urlpatterns = [
    path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),
    path('inquiries/like/', UserInquiryLikeAPIView.as_view(), name="user-inquiries-like"),
]

router = routers.DefaultRouter()
router.register('pages', InstaPageViewSet)

urlpatterns = router.urls
