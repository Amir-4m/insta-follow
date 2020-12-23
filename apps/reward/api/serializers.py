from datetime import datetime

from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.instagram_app.models import InstaPage
from apps.instagram_app.services import CryptoService


class AdViewVerificationSerializer(serializers.Serializer):
    data = serializers.CharField(max_length=256)

    def validate(self, attrs):
        encrypted = attrs['data']
        current_ts = timezone.now().timestamp()
        dt = datetime.utcnow().strftime("%d%m%y%H")

        try:
            text = CryptoService(dt + dt).decrypt(encrypted)
        except UnicodeDecodeError:
            raise ValidationError(detail={'detail': _('invalid data!')})

        uuid, ts, _string = text.split('-%25')
        cached_value = cache.get(f'{uuid}-ad')
        cache.delete(f'{uuid}-ad')

        if cached_value != encrypted:
            raise ValidationError(detail={'detail': _('invalid data!')})

        if not InstaPage.objects.filter(uuid=uuid).exists():
            raise ValidationError(detail={'detail': _('invalid page!')})

        if current_ts - float(ts) < 5:
            raise ValidationError(detail={'detail': _('not confirmed!')})

        attrs.update({'page': uuid})
        return attrs

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()
