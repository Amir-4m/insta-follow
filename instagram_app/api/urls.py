from django.urls import path

from .views import InstaPageAPIView, LikedPageAPIVIEW

urlpatterns = [
    path('page/', InstaPageAPIView.as_view(), name="page"),
    path('user/liked/', LikedPageAPIVIEW.as_view(), name="liked"),

]
