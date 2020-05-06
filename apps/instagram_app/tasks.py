import json
import logging
import urllib.parse
import requests

from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from celery import shared_task

from .endpoints import LIKES_BY_SHORTCODE, COMMENTS_BY_SHORTCODE
from .services import InstagramAppService
from .models import Order, UserInquiry, BaseInstaEntity, InstaAction, CoinTransaction

logger = logging.getLogger(__name__)


@shared_task
def collect_like(order_id, order_link, order_page_id):
    model = BaseInstaEntity.get_model(InstaAction.ACTION_LIKE, order_page_id)
    if not model:
        logger.warning(f"can't get model for order: {order_id} to collect likes")
        return

    shortcode = InstagramAppService.get_shortcode(order_link)
    variables = {
        "shortcode": shortcode,
        "first": 50,
    }

    has_next_page = True
    while has_next_page:
        io_likes = []
        try:
            response = InstagramAppService.req(LIKES_BY_SHORTCODE % urllib.parse.quote_plus(
                json.dumps(variables, separators=(',', ':'))
            ))
            response = response['data']['shortcode_media']
            media_id = response['id']
            response_data = response['edge_liked_by']
            page_info = response_data['page_info']
            edges = response_data['edges']
            for edge in edges:
                node = edge['node']
                io_likes.append(
                    dict(
                        media_url=order_link,
                        media_id=media_id,
                        action=InstaAction.ACTION_LIKE,
                        username=node['username'],
                        user_id=node['id']
                    ))

            objs = model.objects.mongo_insert_many(io_likes)
            if len(objs) != len(io_likes):
                logger.warning(
                    f"bulk create like for order: {order_id}, io_count: {len(io_likes)}, created: {len(objs)}")
                break

            max_id = page_info['end_cursor']
            variables["after"] = max_id
            has_next_page = page_info['has_next_page']
        except Exception as e:
            logger.error(f"getting like error for {order_link} _ {e}")
            break


@shared_task
def collect_comment(order_id, order_link, order_page_id):
    model = BaseInstaEntity.get_model(InstaAction.ACTION_COMMENT, order_page_id)
    if not model:
        logger.warning(f"can't get model for order: {order_id} to collect likes")
        return

    shortcode = InstagramAppService.get_shortcode(order_link)
    variables = {
        "shortcode": shortcode,
        "first": 50,
    }
    media_id = InstagramAppService.get_post_info(order_link)
    has_next_page = True

    while has_next_page:
        io_comments = []
        try:
            response = InstagramAppService.req(COMMENTS_BY_SHORTCODE % urllib.parse.quote_plus(
                json.dumps(variables, separators=(',', ':'))
            ))
            response = response['data']['shortcode_media']
            response_data = response['edge_media_to_parent_comment']
            page_info = response_data['page_info']
            edges = response_data['edges']
            for edge in edges:
                node = edge['node']
                io_comments.append(
                    dict(media_url=order_link,
                         media_id=media_id,
                         action=InstaAction.ACTION_COMMENT,
                         username=node['owner']['username'],
                         user_id=node['owner']['id'],
                         comment=node['text'],
                         comment_id=node['id'],
                         comment_time=datetime.fromtimestamp(node['created_at']))

                )

            objs = model.objects.mongo_insert_many(io_comments)
            if len(objs) != len(io_comments):
                logger.warning(
                    f"bulk create comments for order: {order_id}, io_count: {len(io_comments)}, created: {len(objs)}")
                break

            max_id = page_info['end_cursor']
            variables["after"] = max_id
            has_next_page = page_info['has_next_page']
        except Exception as e:
            logger.error(f"getting comment error for {order_id} link:{order_link} _ {e}")
            break


@shared_task
def collect_post_info(order_id, action, link, media_url, author):
    if action in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]:
        media_id, author, media_url = InstagramAppService.get_post_info(link)

    elif action == InstaAction.ACTION_FOLLOW:
        instagram_username = InstagramAppService.get_page_id(link)
        try:
            response = requests.get(f"https://www.instagram.com/{instagram_username}/?__a=1").json()
            media_url = response['graphql']['user']['profile_pic_url_hd']
            author = instagram_username
        except Exception as e:
            logger.error(f"extract account json got exception error: {e}")
    if media_url and author:
        Order.objects.filter(id=order_id).update(media_url=media_url, instagram_username=author)


# PERIODIC TASK
@shared_task
def collect_order_data():
    lock_key = 'collect-order-data'
    if cache.get(lock_key):
        logger.warning("collecting data for orders process still locked!!")
        return

    cache.set(lock_key, True, 60 * 60)

    orders = Order.objects.filter(is_enable=True)
    for order in orders:
        logger.info(f"collecting data for order: {order.link}")
        try:
            collect_like.delay(order.id, order.link, order.instagram_username)
            collect_comment.delay(order.id, order.link, order.instagram_username)
        except Exception as e:
            logger.error(
                f"collecting data for order: {order.link} error: {e}")

    cache.delete(lock_key)


# PERIODIC TASK
@shared_task
def validate_user_inquiries():
    qs = UserInquiry.objects.filter(done_time__isnull=False, validated_time__isnull=True,
                                    status=UserInquiry.STATUS_DONE)
    inquiries = [(obj.id, obj.user_page) for obj in qs]
    for inquiry in inquiries:
        InstagramAppService.check_user_action([inquiry[0]], inquiry[1])


# PERIODIC TASK
@shared_task
def final_validate_user_inquiries():
    for inquiry in UserInquiry.objects.select_for_update().filter(
            validated_time__isnull=False,
            validated_time__gte=timezone.now() - timedelta(days=1),
            done_time__isnull=False,
            status=UserInquiry.STATUS_DONE
    ):
        inquiry.last_check_time = timezone.now()
        order = Order.objects.select_for_update().filter(id=inquiry.order.id)
        if InstagramAppService.check_activity_from_db(inquiry.order.link, inquiry.user.username, inquiry.order.action):
            inquiry.status = UserInquiry.STATUS_VALIDATED
            CoinTransaction.objects.create(
                user=inquiry.user_page.user,
                inquiry=inquiry,
                amount=order.action.action_value
            )
            if order.achieved_number_approved() == order.target_no:
                order.is_enable = False
                order.save()
        else:
            inquiry.status = UserInquiry.STATUS_REJECTED
        inquiry.save()
