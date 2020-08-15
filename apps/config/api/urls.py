from django.urls import path

from .views import ConfigAPIView

urlpatterns = [
    path('init/', ConfigAPIView.as_view(), name='init'),

]
