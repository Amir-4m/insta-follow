from django.urls import path

from .views import ConfigAPIView

urlpatterns = [
    path('initialize/', ConfigAPIView.as_view(), name='initialize'),

]
