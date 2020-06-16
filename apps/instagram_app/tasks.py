import json
import logging
import time
import urllib.parse
import requests

from datetime import datetime, timedelta

from celery.schedules import crontab
from celery.task import periodic_task
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.db.models import F, Sum, Case, When, IntegerField
from django.utils import timezone
from django.conf import settings

from celery import shared_task
from telegram import Bot

from bot import texts

from .endpoints import LIKES_BY_SHORTCODE, COMMENTS_BY_SHORTCODE
from .services import InstagramAppService, CustomService
from .models import Order, UserInquiry, BaseInstaEntity, InstaAction, CoinTransaction, InstaPage
from ..telegram_app.models import TelegramUser

logger = logging.getLogger(__name__)


@shared_task
def collect_page_info(insta_page_id, instagram_id):
    user_id, name, followers, following, posts_count, media_url, is_private = InstagramAppService.get_page_info(
        instagram_id, full_info=True
    )
    InstaPage.objects.filter(id=insta_page_id).update(
        instagram_user_id=user_id,
        followers=followers,
        following=following,
        post_no=posts_count
    )


@shared_task
def collect_like(order_id, order_link, order_entity):
    try:
        model = BaseInstaEntity.get_model(InstaAction.ACTION_LIKE, order_entity)
        model.objects.mongo_create_index([('user_id', 1), ('action', 1)], unique=True)

    except Exception as e:
        logger.error(f"can't get model for order: {order_id} to collect likes : {e}")
        return

    shortcode = InstagramAppService.get_shortcode(order_link)
    variables = {
        "shortcode": shortcode,
        "first": 50,
    }

    limit = 0
    io_likes = []
    has_next_page = True
    while limit < 2000 and has_next_page:
        try:
            time.sleep(60)
            response = InstagramAppService.req(LIKES_BY_SHORTCODE % urllib.parse.quote_plus(
                json.dumps(variables, separators=(',', ':'))
            ))
            response = response['data']['shortcode_media']
            response_data = response['edge_liked_by']
            page_info = response_data['page_info']
            edges = response_data['edges']
            for edge in edges:
                node = edge['node']

                if not CustomService.mongo_exists(model, user_id=node['id'], action=InstaAction.ACTION_LIKE):
                    limit += 1
                    io_likes.append(
                        dict(
                            action=InstaAction.ACTION_LIKE,
                            username=node['username'],
                            user_id=node['id']
                        ))
                else:
                    limit = 2000
                    break

            max_id = page_info['end_cursor']
            variables["after"] = max_id
            has_next_page = page_info['has_next_page']
        except Exception as e:
            logger.error(f"getting like error for {order_link} _ {e}")
            break
    try:
        io_likes.reverse()
        model.objects.mongo_insert_many(io_likes)
    except Exception as e:
        logger.error(f'mongo insert for order {order_id} collecting like got exception: {e}')


@shared_task
def collect_comment(order_id, order_link, order_entity):
    try:
        model = BaseInstaEntity.get_model(InstaAction.ACTION_COMMENT, order_entity)
        model.objects.mongo_create_index([('user_id', 1), ('action', 1)], unique=True)

    except Exception as e:
        logger.warning(f"can't get model for order: {order_id} to collect comments: {e}")
        return

    shortcode = InstagramAppService.get_shortcode(order_link)
    variables = {
        "shortcode": shortcode,
        "first": 50,
    }

    limit = 0
    io_comments = []

    has_next_page = True
    while limit < 2000 and has_next_page:
        try:
            time.sleep(60)
            response = InstagramAppService.req(COMMENTS_BY_SHORTCODE % urllib.parse.quote_plus(
                json.dumps(variables, separators=(',', ':'))
            ))
            response = response['data']['shortcode_media']
            response_data = response['edge_media_to_parent_comment']
            page_info = response_data['page_info']
            edges = response_data['edges']
            for edge in edges:
                node = edge['node']
                if not CustomService.mongo_exists(model, user_id=node['id'], action=InstaAction.ACTION_COMMENT):
                    io_comments.append(
                        dict(
                            action=InstaAction.ACTION_COMMENT,
                            username=node['owner']['username'],
                            user_id=node['owner']['id'],
                            comment=node['text'],
                            comment_id=node['id'],
                            comment_time=datetime.fromtimestamp(node['created_at']))

                    )
                else:
                    limit = 2000
                    break

            max_id = page_info['end_cursor']
            variables["after"] = max_id
            has_next_page = page_info['has_next_page']
        except Exception as e:
            logger.error(f"getting comment error for {order_id} link:{order_link} _ {e}")
            break
    try:
        io_comments.reverse()
        model.objects.mongo_insert_many(io_comments)
    except Exception as e:
        logger.error(f'mongo insert for order {order_id} collecting comment got exception: {e}')


@shared_task
def collect_follower(order_id, order_entity, order_instagram_id):
    try:
        model = BaseInstaEntity.get_model(InstaAction.ACTION_FOLLOW, order_entity)
        model.objects.mongo_create_index([('user_id', 1), ('action', 1)], unique=True)

    except Exception as e:
        logger.warning(f"can't get model for order: {order_id} to collect followers: {e}")
        return
    try:
        followers = InstagramAppService.get_user_followers(order_instagram_id)
        io_followers = []
        for follower in followers['accounts']:
            if not CustomService.mongo_exists(model, user_id=follower.identifier, action=InstaAction.ACTION_FOLLOW):
                io_followers.append(
                    dict(
                        action=InstaAction.ACTION_FOLLOW,
                        username=follower.username,
                        user_id=follower.identifier
                    ))
            else:
                break
        try:
            io_followers.reverse()
            model.objects.mongo_insert_many(io_followers)
        except Exception as e:
            logger.error(f'mongo insert for order {order_id} collecting like got exception: {e}')
    except Exception as e:
        logger.error(
            f"error occurred for getting followers for order {order_id} and username {order_instagram_id}: {e}")


@shared_task
def collect_order_link_info(order_id, action, link, media_url):
    if action == InstaAction.ACTION_FOLLOW:
        author = InstagramAppService.get_page_id(link)
        entity_id, media_url, is_private = InstagramAppService.get_page_info(author)

    else:
        entity_id, author, media_url, is_private = InstagramAppService.get_post_info(link)
    if is_private:
        incomplete_order_notifier.delay(order_id)

    elif media_url and author and entity_id:
        Order.objects.filter(id=order_id).update(
            entity_id=entity_id,
            media_url=media_url,
            instagram_username=author,
            is_enable=True,
            description=_("order enabled properly")
        )


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
@periodic_task(run_every=(crontab(minute='*/20')), name="collect_order_data", ignore_result=True)
def collect_order_data():
    orders = Order.objects.filter(is_enable=True)
    for order in orders:
        logger.info(f"collecting data for order: {order.link}")
        try:
            if order.action.action_type == InstaAction.ACTION_LIKE:
                collect_like.delay(order.id, order.link, order.entity_id)
            if order.action.action_type == InstaAction.ACTION_COMMENT:
                collect_comment.delay(order.id, order.link, order.entity_id)
            if order.action.action_type == InstaAction.ACTION_FOLLOW:
                collect_follower.delay(order.id, order.entity_id, order.instagram_username)
        except Exception as e:
            logger.error(f"collecting data for order: {order.link} error: {e}")


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
                user_inquiry.order.entity_id,
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
