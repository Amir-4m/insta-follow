import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import CoinPackageOrder, CoinTransaction

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=CoinPackageOrder)
def package_order_receiver(sender, instance, **kwargs):
    if instance._b_is_paid is None and instance.is_paid is True:
        coin_package = instance.coin_package
        ct_amount = coin_package.amount if coin_package.amount_offer is None else coin_package.amount_offer
        CoinTransaction.objects.create(
            page=instance.page,
            amount=ct_amount,
            package=instance,
            transaction_type=CoinTransaction.TYPE_PURCHASE,
        )

# @receiver(post_save, sender=InstaPage)
# def insta_page_receiver(sender, instance, created, raw=False, **kwargs):
#     collect_page_info.delay(insta_page_id=instance.id, instagram_id=instance.instagram_username)
