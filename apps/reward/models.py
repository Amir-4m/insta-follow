from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.instagram_app.models import InstaPage


class AdReward(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    properties = JSONField(_('properties'), default=dict, null=True)
    reward_amount = models.IntegerField(_("reward amount"), blank=True)
    transaction_id = models.CharField(_("transaction id"), max_length=256, blank=True)
    page = models.ForeignKey(InstaPage, related_name='ad_rewards', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('page', 'transaction_id')
