from django.urls import path
from django_admob_ssv.views import admob_ssv

urlpatterns = [
    path('ad_reward/', admob_ssv),
]
