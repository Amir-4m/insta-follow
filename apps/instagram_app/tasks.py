import logging
import requests
from random import choice

from datetime import timedelta

from celery import shared_task
from celery.schedules import crontab
from celery.task import periodic_task
from django.core.cache import cache
from django.db.models import F, Sum, Case, When, IntegerField
from django.utils import timezone
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, InstaAction, CoinTransaction, CoinPackage, InstaPage

logger = logging.getLogger(__name__)


# PERIODIC TASK
@periodic_task(run_every=(crontab(hour='*/17', minute='0')))
def final_validate_user_inquiries():
    user_inquiries = UserInquiry.objects.select_related('order').filter(
        created_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        validated_time__isnull=True,
        status=UserInquiry.STATUS_VALIDATED,
        order__action__action_type=InstaAction.ACTION_FOLLOW,
        order__is_enable=True
    )
    insta_pages = InstaPage.objects.filter(
        instagram_user_id__in=user_inquiries.distinct('order__owner__instagram_user_id').values_list('order__owner__instagram_user_id', flat=True)
    )
    order_usernames = {}
    for page in insta_pages:
        try:
            order_usernames[page.instagram_username] = [
                follower.username for follower in InstagramAppService.get_user_followers(page.session_id, page.instagram_username)
            ]
        except Exception as e:
            logger.error(f"order followers `{page.username}` got exception: {type(e)} - {e}")
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


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/5')))
def update_orders_achieved_number():
    q = Order.objects.filter(is_enable=True).annotate(
        achived_no=Sum(
            Case(
                When(
                    user_inquiries__status=UserInquiry.STATUS_VALIDATED, then=1
                )
            ),
            output_field=IntegerField()
        ),
    )
    try:
        q.filter(
            achived_no__gte=F('target_no')
        ).update(
            is_enable=False,
            description=_("order completed")
        )

        # reactivating orders, which lost their achieved followers
        q.filter(
            achived_no__lt=F('target_no') * settings.ORDER_TARGET_RATIO / 100,
            is_enable=False,
            action=InstaAction.ACTION_FOLLOW,
            updated_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        ).update(
            is_enable=True,
            description=_('order enabled properly.')
        )
    except Exception as e:
        logger.error(f"updating orders achieved number got exception: {e}")


# TODO: Review
"""
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
"""


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*/30')))
def cache_gateways():
    codes = []
    response = CustomService.payment_request('gateways', 'get')
    data = response.json()
    for gateway in data:
        codes.append(gateway['code'])
    cache.set("gateway_codes", codes, None)


@shared_task()
def check_order_validity(order_id):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(f'[order check failed]-[id: {order_id}]-[exc: order does not exists!]')
        return

    page = choice(InstaPage.objects.order_by('-updated_time')[:10])
    try:
        r = requests.get(
            f"{order.link}?__a=1", headers={"User-Agent": f"{timezone.now().isoformat()}"},
            timeout=(3.05, 9),
            cookies={'sessionid': page.session_id},
        )
        r.raise_for_status()
        res = r.json()

    except requests.exceptions.HTTPError as e:
        logger.warning(
            f'[order invalid]-[id: {order.id}, url: {order.link}]-[status code: {e.response.status_code}]')
        if e.response.status_code == 404:
            order.is_enable = False
            order.save()

    except Exception as e:
        logger.error(f'[order check failed]-[id: {order.id}, url: {order.link}]-[exc: {type(e)}, {str(e)}]')
        check_order_validity.delay(order_id)

    else:
        if order.action.action_type == InstaAction.ACTION_FOLLOW:
            order.is_enable = not res['graphql']['user'].get('is_private', False)
        else:
            order.media_properties['media_url'] = res['graphql']['shortcode_media']['display_url']
            order.save()
