import logging
import requests
from celery.schedules import crontab
from celery.task import periodic_task
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django.db.models import F, Sum, Case, When, IntegerField
from django.utils import timezone
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, InstaAction, CoinTransaction, CoinPackage

logger = logging.getLogger(__name__)


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='0', hour='16')), name="final_validate_user_inquiries", ignore_result=True)
def final_validate_user_inquiries():
    open_orders = Order.objects.filter(is_enable=True, action__action_type=InstaAction.ACTION_FOLLOW)
    for order in open_orders:
        order_inquiries = order.user_inquiries.filter(
            updated_time__lt=timezone.now().replace(hour=0, minute=0, second=0),
            validated_time__isnull=True,
            status=UserInquiry.STATUS_VALIDATED,
            order__action__action_type=InstaAction.ACTION_FOLLOW
        )
        if not order_inquiries:
            continue

        try:
            followers = InstagramAppService.get_user_followers(order.instagram_username)
        except Exception as e:
            logger.error(f"final inquiry validation for order {order.id} got exception: {e}")
            continue

        followers_username = [follower.username for follower in followers['accounts']]

        for inquiry in order_inquiries:
            if inquiry.page.instagram_username not in followers_username:
                inquiry.status = UserInquiry.STATUS_REJECTED
                amount = -(inquiry.order.action.action_value * settings.USER_PENALTY_AMOUNT)
                description = _("penalty")
                transaction_type = CoinTransaction.TYPE_PENALTY
                CoinTransaction.objects.create(
                    page=inquiry.page,
                    inquiry=inquiry,
                    amount=amount,
                    description=description,
                    transaction_type=transaction_type
                )
            else:
                inquiry.validated_time = timezone.now()

            inquiry.save()


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/5')), name="update_orders_achieved_number")
def update_orders_achieved_number():
    try:
        Order.objects.filter(is_enable=True).annotate(
            achived_no=Sum(
                Case(
                    When(
                        user_inquiries__status=UserInquiry.STATUS_VALIDATED, then=1
                    )
                ),
                output_field=IntegerField()
            ),
        ).filter(
            achived_no__gte=F('target_no')
        ).update(
            is_enable=False,
            description=_("order completed")
        )
    except Exception as e:
        logger.error(f"updating orders achieved number got exception: {e}")


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/5')), name="update_expired_featured_packages")
def update_expired_featured_packages():
    try:
        CoinPackage.objects.filter(
            featured__lt=timezone.now()
        ).update(
            featured=None
        )
    except Exception as e:
        logger.error(f"updating expired featured packages got error: {e}")


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/30')), name="cache_gateways")
def cache_gateways():
    codes = []
    response = CustomService.payment_request('gateways', 'get')
    data = response.json()
    for gateway in data:
        codes.append(gateway['code'])
    cache.set("gateway_codes", codes, None)
