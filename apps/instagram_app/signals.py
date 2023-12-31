import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CoinPackageOrder, CoinTransaction, ReportAbuse, Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CoinPackageOrder)
def package_order_receiver(sender, instance, **kwargs):
    if instance._b_is_paid is None and instance.is_paid is True:
        coin_package = instance.coin_package
        ct_amount = coin_package.amount_offer or coin_package.amount
        CoinTransaction.objects.create(
            page=instance.page,
            amount=ct_amount,
            package=instance,
            transaction_type=CoinTransaction.TYPE_PURCHASE,
        )


