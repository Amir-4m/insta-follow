from django.db import models
from django.utils.translation import ugettext_lazy as _


class Gateway(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    name = models.CharField(_('name'), max_length=120)
    # method = models.CharField()
