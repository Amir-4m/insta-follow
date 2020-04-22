from django.urls import path
from rest_framework import routers

from .views import UserPageAPIView, LikedPageAPIVIEW

urlpatterns = [
    path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),

]

router = routers.SimpleRouter()
router.register(r'page', UserPageAPIView, basename='UserPage')
urlpatterns += router.urls
