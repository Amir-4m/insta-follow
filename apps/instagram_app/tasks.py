import logging
import requests

from datetime import timedelta

from celery.schedules import crontab
from celery.task import periodic_task
from django.core.cache import cache
from django.db.models import F, Sum, Case, When, IntegerField
from django.utils import timezone
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, InstaAction, CoinTransaction, CoinPackage

logger = logging.getLogger(__name__)


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/17')))
def final_validate_user_inquiries():
    user_inquiries = UserInquiry.objects.select_related('order').filter(
        created_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        validated_time__isnull=True,
        status=UserInquiry.STATUS_VALIDATED,
        order__action__action_type=InstaAction.ACTION_FOLLOW
    )
    order_usernames = {}
    for username in user_inquiries.order_by('order__instagram_username').distinct('order__instagram_username').values(
            'order__instagram_username'):
        try:
            order_usernames[username] = [follower.username for follower in
                                         InstagramAppService.get_user_followers(username)]
        except Exception as e:
            logger.error(f"final inquiry validation for order {username} got exception: {e}")
            continue

    for inquiry in user_inquiries:
        try:
            if inquiry.page.instagram_username not in order_usernames[inquiry.order.instagram_username]:
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
        except Exception as e:
            logger.error(f"validating inquiry {inquiry.id} failed due to : {e}")

    # reactivating orders, which lost their achieved followers
    Order.objects.annotate(
        achived_no=Sum(
            Case(
                When(
                    user_inquiries__status=UserInquiry.STATUS_VALIDATED, then=1
                )
            ),
            output_field=IntegerField()
        ),
    ).filter(
        achived_no__lt=F('target_no') * settings.ORDER_TARGET_RATIO / 100,
        is_enable=False,
        action=InstaAction.ACTION_FOLLOW,
        updated_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
    ).update(
        is_enable=True,
        description=_('order enabled properly.')
    )


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/5')))
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
@periodic_task(run_every=(crontab(minute='*/5')))
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
@periodic_task(run_every=(crontab(minute='*/30')))
def cache_gateways():
    codes = []
    response = CustomService.payment_request('gateways', 'get')
    data = response.json()
    for gateway in data:
        codes.append(gateway['code'])
    cache.set("gateway_codes", codes, None)


# PERIODIC TASK
@periodic_task(run_every=(crontab(hour='*/6')))
def check_orders_posts_existence():
    orders = Order.objects.filter(is_enable=True)
    for order in orders:
        # checking post image signature
        post_url = order.media_properties.get('media_url', '')

        try:
            r = requests.get(post_url, timeout=(3.05, 9))
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.warning(f'[order media invalid]-[{post_url}]-[status code: {e.response.status_code}]')
        except Exception as e:
            logger.error(f'[order media check failed]-[{post_url}]-[exc: {e}]')
        else:
            continue

        try:
            _l = f"{order.link}?__a=1"
            r = requests.get(_l, timeout=(3.05, 9))
            r.raise_for_status()
            res = r.json()
        except requests.exceptions.HTTPError as e:
            logger.warning(f'[order invalid]-[id: {order.id}, url: {_l}]-[status code: {e.response.status_code}]')
            order.is_enable = False
        except Exception as e:
            logger.error(f'[order check failed]-[id: {order.id}, url: {_l}]-[exc: {e}]')
            continue
        else:
            order.media_properties['media_url'] = res['graphql']['shortcode_media']['display_url']

        order.save()
