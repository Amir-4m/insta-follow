import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
from .models import CoinTransaction, Order
from .tasks import collect_post_info

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_coin_transaction(sender, instance, **kwargs):
    if not instance.coin_transactions.exists():
        CoinTransaction.objects.create(user=instance)


@receiver(post_save, sender=Order)
def order_receiver(sender, instance, **kwargs):
    if not instance.media_url or not instance.instagram_username:
        action = instance.action.action_type
        media_url = instance.media_url or ''
        author = instance.instagram_username or ''
        collect_post_info.delay(
            order_id=instance.id,
            action=action,
            link=instance.link,
            media_url=media_url,
            author=author
        )
