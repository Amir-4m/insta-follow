from django.urls import path
from django_admob_ssv.views import admob_ssv
from rest_framework import routers

from .views import TapsellRewardAPIView, DailyRewardAPIView, AdViewVerificationViewsSet, GiftCodeAPIView

urlpatterns = [
    path('ad-reward/google/', admob_ssv),
    path('ad-reward/tapsell/', TapsellRewardAPIView.as_view(), name='tapsell'),
    path('daily-reward/', DailyRewardAPIView.as_view(), name='daily-reward'),
    path('gift-code/', GiftCodeAPIView.as_view(), name='gift-code'),
]

router = routers.DefaultRouter()
router.register('verification', AdViewVerificationViewsSet, basename='verification')

urlpatterns += router.urls
