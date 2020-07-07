import logging
import requests

from datetime import timedelta

from celery.schedules import crontab
from celery.task import periodic_task
from django.utils.translation import ugettext_lazy as _
from django.db.models import F, Sum, Case, When, IntegerField
from django.utils import timezone
from django.conf import settings

from celery import shared_task
from telegram import Bot

from bot import texts

from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, InstaAction, CoinTransaction, InstaPage

logger = logging.getLogger(__name__)


@shared_task()
def collect_page_info(insta_page_id, instagram_id):
    try:
        instapage_url = "https://www.instagram.com/{}/".format(instagram_id)
        response = InstagramAppService.api_call('monitor/insights/', method='post', data={'link': instapage_url})
        response.raise_for_status()
        response_data = response.json()
        user_id = response_data.get('entity_id')
        followers = response_data.get('followers')
        followings = response_data.get('followings')
        posts_count = response_data.get('posts_count')

        InstaPage.objects.filter(id=insta_page_id).update(
            instagram_user_id=user_id,
            followers=followers,
            following=followings,
            post_no=posts_count
        )
    except Exception as e:
        logger.error(f'collecting page info got error: {e}')


@shared_task()
def collect_order_link_info(order_id, action, link, media_url):
    response = InstagramAppService.api_call('monitor/insights/', method='post', data={'link': link})
    response.raise_for_status()
    response_data = response.json()

    entity_id = response_data.get('entity_id')
    media_url = response_data.get('media_url')
    is_private = response_data.get('is_private')
    if action == InstaAction.ACTION_FOLLOW:
        author = InstagramAppService.get_page_id(link)
    else:
        author = response_data.get('author')
    if is_private:
        incomplete_order_notifier.delay(order_id)

    elif media_url and author and entity_id:
        data = {
            'link': link,
            'expire_time': timezone.now().date() + timedelta(days=365)
        }
        res = InstagramAppService.api_call('monitor/orders/', method='post', data=data)
        res.raise_for_status()
        if res.status_code == 201:
            track_id = res.json().get('_id')
            Order.objects.filter(id=order_id).update(
                entity_id=entity_id,
                media_url=media_url,
                instagram_username=author,
                is_enable=True,
                track_id=track_id,
                description=_("order enabled properly")
            )
        else:
            logger.error(f'collect order link info got error :{res.text}')


@shared_task
def incomplete_order_notifier(order_id):
    order = Order.objects.get(id=order_id)
    order.is_enable = False
    order.description = "problem in getting information"
    order.save()
    if hasattr(order.owner, 'telegramuser'):
        bot = Bot(token=settings.TELEGRAM_BOT.get('TOKEN'))

        bot.send_message(
            chat_id=order.owner.telegramuser.telegram_user_id,
            text=texts.ORDER_CREATE_FAILED % order.link,
            disable_web_page_preview=True
        )
    else:
        devices = [device.device_id for device in order.owner.devices.all()]
        if len(devices) >= 1:
            data = {
                "devices": [devices],
                "data": {
                    "title": _("Error in submitting order"),
                    "alert": _("Please make assurance that your instagram page has not any problem) !")
                }
            }
            header = {'Authorization': settings.DEVLYTIC_TOKEN}
            try:
                requests.post(settings.PUSH_API_URL, data, headers=header)
            except Exception as e:
                logger.error(f"push message for private account failed due : {e}")


# PERIODIC TASK
@periodic_task(run_every=(crontab(minute='*')), name="validate_user_inquiries", ignore_result=True)
def validate_user_inquiries():
    # updating expired inquiries status
    UserInquiry.objects.filter(
        status=UserInquiry.STATUS_OPEN, created_time__lt=timezone.now() - timedelta(hours=2)
    ).update(status=UserInquiry.STATUS_EXPIRED)

    # updating rejected like and comment inquiries status
    UserInquiry.objects.filter(
        status=UserInquiry.STATUS_DONE,
        updated_time__lt=timezone.now() - timedelta(hours=2),
        order__action__in=[InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]
    ).update(status=UserInquiry.STATUS_REJECTED)

    done_inquiries = UserInquiry.objects.select_related('user_page', 'user_page__page').filter(
        status=UserInquiry.STATUS_DONE
    )
    # validating inquiries and create coin for validated like and comment inquiries
    for user_inquiry in done_inquiries:
        if CustomService.check_activity_from_db(
                user_inquiry.user_page.page.instagram_user_id,
                user_inquiry.order.track_id,
                user_inquiry.order.action.action_type
        ):
            user_inquiry.status = UserInquiry.STATUS_VALIDATED
            if user_inquiry.order.action.action_type in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]:
                user_inquiry.validated_time = timezone.now()
                CoinTransaction.objects.create(
                    user=user_inquiry.user_page.user,
                    inquiry=user_inquiry,
                    amount=user_inquiry.order.action.action_value,
                    description=f"validated inquiry {user_inquiry.id}"
                )
            user_inquiry.save()


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
            if inquiry.user_page.page.instagram_username in followers_username:
                inquiry.validated_time = timezone.now()
                amount = inquiry.order.action.action_value
                description = f"validated inquiry {inquiry.id}"
            else:
                inquiry.status = UserInquiry.STATUS_REJECTED
                amount = -(inquiry.order.action.action_value * settings.USER_PENALTY_AMOUNT)
                description = f"rejected inquiry {inquiry.id}"

            inquiry.save()
            CoinTransaction.objects.create(
                user=inquiry.user_page.user,
                inquiry=inquiry,
                amount=amount,
                description=description
            )


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
@periodic_task(run_every=(crontab(minute='*/30')), name="check_expired_inquiries")
def check_expired_inquiries():
    UserInquiry.objects.filter(
        status=UserInquiry.STATUS_OPEN,
        created_time__lt=timezone.now() - timedelta(hours=2)
    ).update(status=UserInquiry.STATUS_EXPIRED)
