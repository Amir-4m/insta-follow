import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
from .models import CoinTransaction, Order
from .tasks import collect_post_info

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=UserPackage)
# def save_remaining(sender, instance, **kwargs):
#     follow = instance.remaining_follow
#     like = instance.remaining_like
#     comment = instance.remaining_comment
#     if follow is None:
#         follow = instance.package.follow_target_no
#     if like is None:
#         like = instance.package.like_target_no
#     if comment is None:
#         comment = instance.package.comment_target_no
#     UserPackage.objects.filter(
#         id=instance.id).update(
#         remaining_follow=follow,
#         remaining_comment=comment,
#         remaining_like=like
#     )


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
