from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Gateway(models.Model):
    TYPE_BANK = 1
    TYPE_PSP = 2
    GATEWAY_TYPES = (
        (TYPE_BANK, _('BANK')),
        (TYPE_PSP, _('PSP')),
    )

    FUNCTION_SAMAN = 1
    FUNCTION_BAZAAR = 2
    GATEWAY_FUNCTIONS = (
        (FUNCTION_SAMAN, _('Saman')),
        (FUNCTION_BAZAAR, _('Bazaar')),
    )

    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    display_name = models.CharField(_('display name'), max_length=120)
    title = models.CharField(_('title'), max_length=120)
    image = models.ImageField(upload_to='gateways/images', blank=True)
    url = models.CharField(_("request url"), max_length=150, blank=True)
    check_url = models.CharField(_("pay check url"), max_length=150, blank=True)
    gw_type = models.PositiveSmallIntegerField(_("type"), choices=GATEWAY_TYPES, default=TYPE_BANK)
    code = models.PositiveSmallIntegerField(_("code"), choices=GATEWAY_FUNCTIONS, default=FUNCTION_SAMAN)
    merchant_id = models.CharField(_("merchant id"), max_length=50, blank=True)
    merchant_pass = models.CharField(_("merchant pass"), max_length=50, blank=True)
    is_enable = models.BooleanField(default=True)

    def clean(self):
        if self.gw_type == self.TYPE_BANK and (not self.merchant_pass or not self.merchant_id):
            raise ValidationError(_("merchant pass and merchant id could not be none in type bank!"))
