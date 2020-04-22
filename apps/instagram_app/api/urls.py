from django.urls import path
from rest_framework import routers

from .views import InstaPageViewSet, LikedPageAPIVIEW

urlpatterns = [
    path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),

]
router = routers.DefaultRouter()
router.register('user/page', InstaPageViewSet, basename="InstaPage")

urlpatterns += router.urls
