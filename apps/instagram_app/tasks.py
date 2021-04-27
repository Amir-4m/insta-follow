import logging
import requests
from random import choice

from datetime import timedelta

from celery import shared_task
from celery.schedules import crontab
from celery.task import periodic_task
from django.core.cache import cache
from django.db.models import F, Sum, Case, When, IntegerField, Min
from django.utils import timezone
from django.conf import settings

from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, InstaAction, CoinTransaction, InstaPage

logger = logging.getLogger(__name__)


@shared_task()
def validate_user_inquiries_for_order_link(page_id, username, user_id, session_id):
    try:
        page_followings = InstagramAppService.get_user_followings(session_id, user_id)
        logger.info(f"[validate_user_inquiries]-[followings for page: {username}]-[following count: {len(page_followings)}]")
    except Exception as e:
        logger.error(f"[validate_user_inquiries]-[followings for page: {username}]-[{type(e)}]-[err: {e}]")
        return

    user_inquiries = UserInquiry.objects.select_related('order').filter(
        created_time__lte=timezone.now().date() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        validated_time__isnull=True,
        status=UserInquiry.STATUS_VALIDATED,
        order__action__action_type=InstaAction.ACTION_FOLLOW,
        page_id=page_id
    )

    validated_ids = []
    for inquiry in user_inquiries:
        page_username = InstagramAppService.get_page_id(inquiry.order.link)
        if page_username in page_followings:
            logger.info(f"[validate_user_inquiries]-[page: {username}]-[{page_username} still followed]")
            validated_ids.append(inquiry.id)
        else:
            logger.info(f"[validate_user_inquiries]-[page: {username}]-[{page_username} not followed]")
            inquiry.status = UserInquiry.STATUS_REJECTED
            amount = -(inquiry.order.action.action_value * settings.USER_PENALTY_AMOUNT)
            CoinTransaction.objects.create(
                page=inquiry.page,
                inquiry=inquiry,
                amount=amount,
                transaction_type=CoinTransaction.TYPE_PENALTY
            )
            inquiry.save()

    UserInquiry.objects.filter(id__in=validated_ids).update(validated_time=timezone.now())


@periodic_task(run_every=(crontab(hour='4', minute='30')))
def validate_user_inquiries():
    qs = UserInquiry.objects.filter(
        created_time__lte=timezone.now().date() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
        validated_time__isnull=True,
        status=UserInquiry.STATUS_VALIDATED,
        order__action__action_type=InstaAction.ACTION_FOLLOW,
    )

    # set validated for all inquiries after 7 days
    qs.filter(
        created_time__lte=timezone.now().date() - timedelta(days=7)
    ).update(validated_time=timezone.now())

    order_links = set(Order.objects.filter(
        id__in=qs.values_list('order_id', flat=True)
    ).values_list('link', flat=True))

    session_id = None
    for order_link in order_links:
        page_username = InstagramAppService.get_page_id(order_link)

        # get random session id
        if session_id is None:
            try:
                random_recent_insta_page = InstaPage.objects.filter(updated_time__gt=timezone.now().date()).order_by('?')[0]
                session_id = random_recent_insta_page.session_id
            except:
                continue

        is_private = InstagramAppService.page_private(page_username, session_id)
        if is_private is None:
            # session_id is expired or useless
            session_id = None
        elif is_private is True:
            UserInquiry.objects.filter(
                order__link=order_link,
                status=UserInquiry.STATUS_VALIDATED,
                validated_time__isnull=True,
            ).update(
                validated_time=timezone.now()
            )
            logger.info(f"[validate_user_inquiries]-[page `{page_username}` is private]")

    pages = set(qs.values_list('page_id', 'page__instagram_username', 'page__instagram_user_id', 'page__session_id'))
    for page_id, username, user_id, session_id in pages:
        logger.info(f"[validate_user_inquiries]-[page: {username}]")
        validate_user_inquiries_for_order_link.delay(page_id, username, user_id, session_id)


@periodic_task(run_every=(crontab(minute='*')))
def update_orders_achieved_number():
    Order.objects.filter(status=Order.STATUS_ENABLE).annotate(
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
        status=Order.STATUS_COMPLETE,
    )

    # reactivating orders, which lost their achieved followers
    Order.objects.filter(
        status=Order.STATUS_COMPLETE,
        action=InstaAction.ACTION_FOLLOW,
        updated_time__lte=timezone.now() - timedelta(hours=settings.PENALTY_CHECK_HOUR),
    ).annotate(
        achived_no=Sum(
            Case(
                When(
                    user_inquiries__status=UserInquiry.STATUS_VALIDATED,
                    user_inquiries__validated_time__isnull=False,
                    then=1
                )
            ),
            output_field=IntegerField()
        ),
    ).filter(
        achived_no__lt=F('target_no') * settings.ORDER_TARGET_RATIO / 100,
    ).update(
        status=Order.STATUS_ENABLE,
    )


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
        return

    else:
        try:
            if order.action.action_type == InstaAction.ACTION_FOLLOW:
                if res['graphql']['user'].get('is_private', False):
                    order.status = Order.STATUS_DISABLE
                    order.description = "(Private Page) - Order is disabled due to page being private"
                    order.user_inquiries.filter(
                        validated_time__isnull=True, status=UserInquiry.STATUS_VALIDATED
                    ).update(validated_time=timezone.now())

            else:
                if order.action.action_type == InstaAction.ACTION_COMMENT and res['graphql']['shortcode_media']['comments_disabled']:
                    order.status = Order.STATUS_DISABLE
                    order.description = "(Post Comment) - Order is disabled due to disabled commenting"

                order.media_properties['media_url'] = res['graphql']['shortcode_media']['display_url']
        except KeyError:
            order.status = Order.STATUS_DISABLE
            order.description = f"(Order Unavailable) - Order is disabled - res: {res}"

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
