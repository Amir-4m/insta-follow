from django.urls import path
from rest_framework import routers

from .views import InstaPageViewSet, LikedPageAPIVIEW


router = routers.DefaultRouter()
router.register('pages', InstaPageViewSet)

urlpatterns = router.urls

# urlpatterns += [
#     path('likes/', LikedPageAPIVIEW.as_view(), name="user-likes"),
#
# ]
