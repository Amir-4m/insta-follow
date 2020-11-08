from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.instagram_app.models import InstaPage


class AdReward(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    ad_network = models.IntegerField(_("ad network"), blank=True, null=True)
    ad_unit = models.IntegerField(_("ad unit"), blank=True, null=True)
    custom_data = models.TextField(_("custom data"), blank=True)
    key_id = models.IntegerField(_("key id"))
    reward_amount = models.IntegerField(_("reward amount"), blank=True)
    reward_item = models.CharField(_("reward item"), max_length=512, blank=True)
    signature = models.CharField(_("signature"), max_length=512)
    transaction_id = models.CharField(_("transaction id"), max_length=256, blank=True)
    page = models.ForeignKey(InstaPage, related_name='ad_rewards', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('page', 'transaction_id')
