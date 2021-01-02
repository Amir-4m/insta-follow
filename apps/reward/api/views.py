from datetime import datetime

import requests
from django.core.cache import cache
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.instagram_app.authentications import PageAuthentication
from apps.instagram_app.models import CoinTransaction, InstaPage
from apps.instagram_app.permissions import PagePermission
from apps.instagram_app.services import CryptoService
from apps.reward.api.serializers import AdViewVerificationSerializer
from apps.reward.models import AdReward
from apps.reward.swagger_schemas import DAILY_REWARD_DOCS_RESPONSE, TAPSELL_REWARD_DOCS, TAPSELL_REWARD_DOCS_RESPONSE
from conf import settings


class DailyRewardAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @swagger_auto_schema(
        operation_description='Reward page daily with a specific amount of coins',
        responses={200: DAILY_REWARD_DOCS_RESPONSE}
    )
    def get(self, request, *args, **kwargs):
        page = request.auth['page']
        reward_amount = settings.COIN_DAILY_REWARD_AMOUNT
        if CoinTransaction.objects.filter(
                created_time__gte=timezone.now().replace(hour=0, minute=0, second=0),
                transaction_type=CoinTransaction.TYPE_DAILY_REWARD,
                page=page
        ).exists():
            rewarded = False
        else:
            CoinTransaction.objects.create(
                page=page,
                description=_("daily reward"),
                amount=reward_amount,
                transaction_type=CoinTransaction.TYPE_DAILY_REWARD
            )
            rewarded = True
        return Response({'page': page.instagram_username, 'amount': reward_amount, 'rewarded': rewarded})


class TapsellRewardAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @swagger_auto_schema(
        operation_description='Reward the page, if page has viewed the ad properly',
        request_body=TAPSELL_REWARD_DOCS,
        responses={200: TAPSELL_REWARD_DOCS_RESPONSE}
    )
    def post(self, request, *args, **kwargs):
        suggestion_id = request.data.get('suggestion_id')
        # event = request.data.get('event')
        if suggestion_id is None:
            raise ValidationError(detail={'detail': _('suggestion_id is required!')})
        response = requests.post(
            url='http://api.tapsell.ir/v2/suggestions/validate-suggestion/',
            json={"suggestionId": suggestion_id}
        )
        is_valid = response.json().get('valid', False)
        if is_valid:
            page = request.auth['page']

            reward = settings.COIN_AD_VIEW_REWARD_AMOUNT

            CoinTransaction.objects.create(
                page=page,
                amount=reward,
                description=_('ad reward'),
                transaction_type=CoinTransaction.TYPE_AD_REWARD
            )
            AdReward.objects.create(
                reward_amount=reward,
                transaction_id=suggestion_id,
                page=page,
            )
        return Response({'valid': is_valid})


class AdViewVerificationViewsSet(viewsets.ViewSet):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @action(methods=['get'], detail=False, url_path='token')
    def token(self, request, *args, **kwargs):
        page = request.auth['page']
        dt = datetime.utcnow().strftime("%d%m%y%H")
        text = f'{page.uuid}-%25{timezone.now().timestamp()}-%25'
        text += str(get_random_string(64 - len(text)))
        encrypted_text = CryptoService(dt + dt).encrypt(text)
        cache.set(f'{page.uuid}-ad', encrypted_text.decode('utf-8'), 70)
        return Response({'data': encrypted_text})

    @action(methods=['post'], detail=False, url_path='verify')
    def verify(self, request, *args, **kwargs):
        serializer = AdViewVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        page = InstaPage.objects.get(uuid=serializer.validated_data['page'])
        CoinTransaction.objects.create(
            page=page,
            amount=settings.COIN_AD_VIEW_REWARD_AMOUNT,
            description=_('ad reward'),
            transaction_type=CoinTransaction.TYPE_AD_REWARD
        )
        AdReward.objects.create(
            reward_amount=settings.COIN_AD_VIEW_REWARD_AMOUNT,
            page=page,
            transaction_id=serializer.validated_data['data']
        )
        return Response({'valid': True})
