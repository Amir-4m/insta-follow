from django.urls import path
from django.conf import settings

from . import views

webhook_prefix = settings.TELEGRAM_BOT.get('WEBHOOK_PREFIX', '')

urlpatterns = [
    path(f"{webhook_prefix}<str:token>/", views.web_hook, name='telegram-webhook'),
]
