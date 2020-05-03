import json
import logging
import urllib.parse
from datetime import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.core.cache import cache

from celery import shared_task

from .endpoints import LIKES_BY_SHORTCODE, COMMENTS_BY_SHORTCODE
from .services import InstagramAppService
from .models import Order, UserInquiry, UserPage, BaseInstaEntity

logger = logging.getLogger(__name__)


@shared_task
def check_user_action(user_inquiry_ids, user_page_id):
    user_page = UserPage.objects.get(id=user_page_id)
    with transaction.atomic():
        for user_inquiry in UserInquiry.objects.select_for_update().filter(id__in=user_inquiry_ids):
            user_inquiry.last_check_time = timezone.now()
            if user_inquiry.validated_time is not None:
                continue
            if InstagramAppService.check_activity_from_db(
                    user_inquiry.order.link,
                    user_page.user.username,
                    user_inquiry.order.action_type):
                user_inquiry.validated_time = timezone.now()
                Order.objects.select_for_update().filter(
                    id=user_inquiry.order.id,
                ).update(
                    achieved_no=F('achieved_no') + 1)
            user_inquiry.save()


@shared_task
def collect_like(order_id, order_link):
    model = BaseInstaEntity.get_model('L', order_link)
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
                        action_type='L',
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
def collect_comment(order_id, order_link):
    model = BaseInstaEntity.get_model('C', order_link)
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
                         action_type='C',
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
            collect_like.delay(order.id, order.link)
            collect_comment.delay(order.id, order.link)
        except Exception as e:
            logger.error(
                f"collecting data for order: {order.link} error: {e}")

    cache.delete(lock_key)
