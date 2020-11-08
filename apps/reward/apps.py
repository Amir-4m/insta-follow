from django.apps import AppConfig


class RewardConfig(AppConfig):
    name = 'apps.reward'

    def ready(self):
        from . import signals  # noqa
