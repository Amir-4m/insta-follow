from django.urls import path
from django_admob_ssv.views import admob_ssv
from .views import TapsellRewardAPIView
from .views import DailyRewardAPIView

urlpatterns = [
    path('ad-reward/google/', admob_ssv),
    path('ad-reward/tapsell/', TapsellRewardAPIView.as_view(), name='tapsell'),
    path('daily-reward/', DailyRewardAPIView.as_view(), name='daily-reward')

]
