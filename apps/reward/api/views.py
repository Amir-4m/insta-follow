from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views
from rest_framework.response import Response

from apps.instagram_app.authentications import PageAuthentication
from apps.instagram_app.models import CoinTransaction
from apps.instagram_app.permissions import PagePermission
from apps.reward.swagger_schemas import DAILY_REWARD_DOCS_RESPONSE
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
                description=_("daily reward"),
                page=page
        ).exists():
            rewarded = False
        else:
            CoinTransaction.objects.filter(
            )
            CoinTransaction.objects.create(
                page=page,
                description=_("daily reward"),
                amount=reward_amount
            )
            rewarded = True
        return Response({'page': page.instagram_username, 'amount': reward_amount, 'rewarded': rewarded})
