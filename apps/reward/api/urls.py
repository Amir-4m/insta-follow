from django.urls import path
from django_admob_ssv.views import admob_ssv

from .views import DailyRewardAPIView

urlpatterns = [
    path('ad_reward/', admob_ssv),
    path('daily-reward/', DailyRewardAPIView.as_view(), name='daily-reward')

]
