from django.apps import AppConfig


class InstagramAppConfig(AppConfig):
    name = 'apps.instagram_app'

    def ready(self):
        from . import signals  # noqa
