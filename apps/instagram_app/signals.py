import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
from .models import CoinTransaction, Order
from .tasks import collect_order_link_info

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_coin_transaction(sender, instance, **kwargs):
    if not instance.coin_transactions.exists():
        CoinTransaction.objects.create(user=instance, amount=0)


@receiver(post_save, sender=Order)
def order_receiver(sender, instance, **kwargs):
    if instance.is_enable is False or instance.entity_id is None:
        action = instance.action.action_type
        media_url = instance.media_url or ''
        collect_order_link_info.delay(
            order_id=instance.id,
            action=action,
            link=instance.link,
            media_url=media_url,
        )
