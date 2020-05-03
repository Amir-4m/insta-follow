import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
from .models import UserPackage, CoinTransaction, Order, Action
from .services import InstagramAppService


@receiver(post_save, sender=UserPackage)
def save_remaining(sender, instance, **kwargs):
    follow = instance.remaining_follow
    like = instance.remaining_like
    comment = instance.remaining_comment
    if follow is None:
        follow = instance.package.follow_target_no
    if like is None:
        like = instance.package.like_target_no
    if comment is None:
        comment = instance.package.comment_target_no
    UserPackage.objects.filter(
        id=instance.id).update(
        remaining_follow=follow,
        remaining_comment=comment,
        remaining_like=like
    )


@receiver(post_save, sender=User)
def user_coin_transaction(sender, instance, **kwargs):
    if not instance.coin_transactions.exists():
        CoinTransaction.objects.create(user=instance)


@receiver(post_save, sender=Order)
def order_media_url_setter(sender, instance, **kwargs):
    action = instance.action_type
    if action == Action.LIKE or action == Action.COMMENT:
        shortcode = InstagramAppService.get_shortcode(instance.link)
        media_url = InstagramAppService.get_post_media_url(shortcode)

    elif action == Action.FOLLOW:
        instagram_username = InstagramAppService.get_page_id(instance.link)
        response = requests.get(f"https://www.instagram.com/{instagram_username}/?__a=1").json()
        media_url = response['graphql']['user']['profile_pic_url_hd']

    Order.objects.filter(
        id=instance.id).update(
        media_url=media_url
    )
    instance.refresh_from_db()
