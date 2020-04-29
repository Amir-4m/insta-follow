import json
import logging
import urllib.parse
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.conf import settings
from celery import shared_task

from .endpoints import LIKES_BY_SHORTCODE, COMMENTS_BY_SHORTCODE
from .services import InstagramAppService
from .models import Order, Action, UserInquiry, UserPage, CoinTransaction

logger = logging.getLogger(__name__)


@shared_task
def check_user_action(user_inquiry_id, user_page_id, link, mode):
    coin_amount = 0
    user_page = UserPage.objects.get(id=user_page_id)
    variables = {
        "shortcode": InstagramAppService.get_shortcode(link),
        "first": 50,
    }
    mode_links = {
        'L': LIKES_BY_SHORTCODE,
        'C': COMMENTS_BY_SHORTCODE
    }
    mode_key = {
        'L': 'edge_liked_by',
        'C': 'edge_media_to_parent_comment'
    }

    search_mode = mode_key[mode]
    found = False
    has_next_page = True
    while not found and has_next_page:
        try:
            response = InstagramAppService.req(
                mode_links[mode] % urllib.parse.quote_plus(
                    json.dumps(
                        variables, separators=(',', ':')
                    )
                )
            )
            response = response['data']['shortcode_media']
            response_data = response[search_mode]
            page_info = response_data['page_info']
            edges = response_data['edges']
            if mode == Action.LIKE:
                for edge in edges:
                    user = edge['node']
                    username = user['username']
                    if username == user_page.page.instagram_username:
                        found = True
                        coin_amount = settings.LIKE_COIN
                        # TODO: async task for creating BaseEntity object for like
            elif mode == Action.COMMENT:
                for edge in edges:
                    user = edge['node']
                    username = user['owner']['username']
                    text = user['text']
                    if username == user_page.page.instagram_username:
                        found = True
                        coin_amount = settings.COMMENT_COIN
                        # TODO: async task for creating BaseEntity object for comment
            max_id = page_info['end_cursor']
            variables["after"] = max_id
            has_next_page = page_info['has_next_page']

        except Exception as e:
            logger.error(f"got error while getting {link} {mode}s {e}")
            break

        with transaction.atomic():
            try:
                user_inquiry = UserInquiry.objects.select_for_update().get(id=user_inquiry_id)
            except UserInquiry.DoesNotExist:
                logger.error(f"user inquiry {user_inquiry_id} with null validated time does not exist!")
                return

            if user_inquiry.validated_time is not None:
                return

            user_inquiry.last_check_time = timezone.now()
            if found:
                user_inquiry.validated_time = timezone.now()
                Order.objects.select_for_update().filter(id=user_inquiry.order.id, action_type=mode).update(
                    achieved_no=F('achieved_no') + 1)
                CoinTransaction.objects.create(user=user_page.user, amount=coin_amount, action=mode)

            user_inquiry.save()
