from django.db import models
from apps.accounts.models import User
from django.utils.translation import ugettext_lazy as _


class TelegramUser(User):
    telegram_user_id = models.BigIntegerField(_("telegram user id"), unique=True)
    is_enable = models.BooleanField(_("is enable?"), default=True)
    first_name = models.CharField(_("first name"), max_length=50, blank=True)

    class Meta:
        db_table = "telegram_user"

    def __str__(self):
        return f"{self.first_name} - {self.telegram_user_id}"
