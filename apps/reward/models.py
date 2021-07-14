import random

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.instagram_app.models import InstaPage


def code_generator():
    return random.randint(100000, 999999)


class AdReward(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    properties = JSONField(_('properties'), default=dict, null=True)
    reward_amount = models.IntegerField(_("reward amount"), blank=True)
    transaction_id = models.CharField(_("transaction id"), max_length=256, blank=True)
    page = models.ForeignKey(InstaPage, related_name='ad_rewards', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('page', 'transaction_id')


class GiftCode(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)

    code = models.CharField(_('code'), max_length=6, default=code_generator)
    amount = models.PositiveSmallIntegerField(_('coin amount'))
    page = models.ForeignKey(InstaPage, related_name='gift_code', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'code: {self.code} - gift coin: {self.amount}'

