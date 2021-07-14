from datetime import datetime

from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.instagram_app.models import InstaPage, CoinTransaction
from apps.instagram_app.services import CryptoService
from apps.reward.models import GiftCode


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
        cached_value = cache.get(f'{uuid}-ad-{encrypted}')

        if cached_value != encrypted:
            raise ValidationError(detail={'detail': _('token expired!')})

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


class GiftCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            attrs['gift_code'] = GiftCode.objects.get(code=attrs['code'])
        except GiftCode.DoesNotExist:
            raise ValidationError(detail={'code': 'Gift code is invalid.'})

        if attrs['gift_code'].page:
            raise ValidationError(detail={'code': 'Gift code used.'})

        return attrs

    def create(self, validated_data):
        gift_code = validated_data['gift_code']
        page = self.context.get('page')

        ct = CoinTransaction.objects.create(
            page=page,
            transaction_type=CoinTransaction.TYPE_GIFT,
            amount=gift_code.amount
        )
        gift_code.page = page
        gift_code.save()

        return gift_code
