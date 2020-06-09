import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import InstaPage, Order
from .tasks import collect_order_link_info, collect_page_info

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def order_receiver(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        action = instance.action.action_type
        media_url = instance.media_url or ''
        collect_order_link_info.delay(
            order_id=instance.id,
            action=action,
            link=instance.link,
            media_url=media_url,
        )


@receiver(post_save, sender=InstaPage)
def insta_page_receiver(sender, instance, created, raw=False, **kwargs):
    collect_page_info.delay(insta_page_id=instance.id, instagram_id=instance.instagram_username)
