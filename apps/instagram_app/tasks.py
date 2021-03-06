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

from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, InstaAction, CoinTransaction, InstaPage

logger = logging.getLogger(__name__)


# PERIODIC TASK
@periodic_task(run_every=(crontab(hour='*/17', minute='30')))
def final_validate_user_inquiries():
    user_inquiries = UserInquiry.objects.select_related('order').filter(
        created_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        validated_time__isnull=True,
        status=UserInquiry.STATUS_VALIDATED,
        order__action__action_type=InstaAction.ACTION_FOLLOW,
        order__status=Order.STATUS_ENABLE
    )
    insta_pages = InstaPage.objects.filter(
        instagram_user_id__in=user_inquiries.distinct('order__owner__instagram_user_id').values_list(
            'order__owner__instagram_user_id', flat=True)
    )
    order_usernames = {}
    for page in insta_pages:
        if InstagramAppService.page_private(page) is True:
            user_inquiries.filter(order__owner=page).update(validated_time=timezone.now())
            logger.warning(f"page `{page.instagram_username}` is private")
            continue

        try:
            order_usernames[page.instagram_username] = [
                follower.username for follower in
                InstagramAppService.get_user_followers(page.session_id, page.instagram_username)
            ]
        except Exception as e:
            logger.error(f"page followers `{page.instagram_username}` got exception: {type(e)} - {str(e)}")
            continue

    for inquiry in user_inquiries:
        try:
            if inquiry.page.instagram_username not in order_usernames[inquiry.order.instagram_username]:
                inquiry.status = UserInquiry.STATUS_REJECTED
                amount = -(inquiry.order.action.action_value * settings.USER_PENALTY_AMOUNT)
                CoinTransaction.objects.create(
                    page=inquiry.page,
                    inquiry=inquiry,
                    amount=amount,
                    transaction_type=CoinTransaction.TYPE_PENALTY
                )
            else:
                inquiry.validated_time = timezone.now()
            inquiry.save()
        except Exception as e:
            logger.error(f"validating inquiry {inquiry.id} failed due to: {type(e)} - {str(e)}")


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*')))
def update_orders_achieved_number():
    q = Order.objects.filter(status=Order.STATUS_ENABLE).annotate(
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
            status=Order.STATUS_COMPLETE,
        )

        # reactivating orders, which lost their achieved followers
        q.filter(
            achived_no__lt=F('target_no') * settings.ORDER_TARGET_RATIO / 100,
            status=Order.STATUS_COMPLETE,
            action=InstaAction.ACTION_FOLLOW,
            updated_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        ).update(
            status=Order.STATUS_ENABLE,
        )
    except Exception as e:
        logger.error(f"updating orders achieved number got exception: {e}")

    return q.count()


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
    data = CustomService.payment_request('gateways', 'get')
    cache.set("gateways", data, None)


@shared_task()
def check_order_validity(order_id):
    try:
        order = Order.objects.get(pk=order_id, status=Order.STATUS_ENABLE)
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
        logger.warning(f'[order invalid]-[id: {order.id}, url: {order.link}]-[status code: {e.response.status_code}]')
        if e.response.status_code == 404:
            order.status = Order.STATUS_DISABLE
            order.description = "(Page Not Found) - Cannot get page info"

    except Exception as e:
        logger.error(f'[order check failed]-[id: {order.id}, url: {order.link}]-[exc: {type(e)}, {str(e)}]')
        check_order_validity.delay(order_id)

    else:
        if order.action.action_type == InstaAction.ACTION_FOLLOW:
            if res['graphql']['user'].get('is_private', False):
                order.status = Order.STATUS_DISABLE
                order.description = "(Private Page) - Order is disabled due to page being private"
        else:
            order.media_properties['media_url'] = res['graphql']['shortcode_media']['display_url']

    order.save()


@periodic_task(run_every=(crontab(minute=0)))
def check_orders_media():
    orders = Order.objects.filter(
        status=Order.STATUS_ENABLE,
        action__action_type__in=(InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT)
    ).order_by('updated_time')
    for order in orders:
        # checking post image signature
        post_url = order.media_properties.get('media_url', '')

        try:
            r = requests.get(post_url, timeout=(3.05, 9))
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.warning(f'[order media invalid]-[{post_url}]-[status code: {e.response.status_code}]')
            if e.response.status_code == 429:
                break
            check_order_validity.delay(order.id)
        except Exception as e:
            logger.error(f'[order media check failed]-[{post_url}]-[exc: {e}]')
