import logging

from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from django_admob_ssv.signals import valid_admob_ssv

from apps.instagram_app.models import InstaPage, CoinTransaction
from .models import AdReward

logger = logging.getLogger(__name__)


@receiver(valid_admob_ssv)
def reward_user(sender, query, **kwargs):
    reward_amount = query.get('reward_amount')
    reward_item = query.get('reward_item')
    transaction_id = query.get('transaction_id')
    user_id = query.get('user_id')
    try:
        page = InstaPage.objects.get(uuid=user_id)
    except InstaPage.DoesNotExist:
        logger.error(f'error in validating user ad reward: user with uuid {user_id} does not exists !')
        return
    if AdReward.objects.filter(page=page, transaction_id=transaction_id).exists():
        return

    logger.info(f'Valid SSV! Reward item: {reward_item}, Reward amount: {reward_amount}, User ID: {user_id}')

    CoinTransaction.objects.create(
        page=page,
        amount=reward_amount,
        description=_("ad reward")
    )
    AdReward.objects.create(
        properties=query,
        reward_amount=reward_amount,
        transaction_id=transaction_id,
        page=page,
    )
