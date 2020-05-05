import json
import logging
import re
import time
import requests
from django.db.models import Sum
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from .models import Order, BaseInstaEntity, InstaPage, InstaAction, CoinTransaction, UserPage, UserInquiry

logger = logging.getLogger(__name__)


class InstagramAppService(object):
    @staticmethod
    def get_page_info(instagram_id):
        try:
            response = requests.get(f"https://www.instagram.com/{instagram_id}/?__a=1").json()
            temp = response['graphql']['user']
            user_id = temp['id']
            name = temp['full_name']
            followers = temp['edge_followed_by']['count']
            following = temp['edge_follow']['count']
            posts_count = temp['edge_owner_to_timeline_media']['count']
            return user_id, name, followers, following, posts_count

        except json.JSONDecodeError:
            logger.error('instagram account response can not be json decoded')

    @staticmethod
    def create_order(user, follow=None, like=None, comment=None, link=None, page_id=None):
        instagram_page = InstaPage.objects.get(id=page_id)
        created_orders = []
        if instagram_page:
            if follow:
                page_url = 'https://www.instagram.com/%s' % instagram_page.instagram_username
                action_value = InstaAction.objects.get(action_type=InstaAction.ACTION_FOLLOW).buy_value
                if user.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet') >= action_value:
                    follow_order = Order.objects.create(
                        action=InstaAction.ACTION_FOLLOW,
                        link=page_url,
                        target_no=follow,
                    )
                    CoinTransaction.objects.create(user=user, amount=-action_value, order=follow_order)
                    created_orders.append(follow_order)
                else:
                    raise ValidationError(_("You do not have enough coin to create follow order"))

        if link:
            if like:
                action_value = InstaAction.objects.get(action_type=InstaAction.ACTION_LIKE).buy_value
                if user.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet') >= action_value:
                    like_order = Order.objects.create(
                        action=InstaAction.ACTION_LIKE,
                        link=link,
                        target_no=like,
                    )
                    CoinTransaction.objects.create(user=user, amount=-action_value, order=like_order)
                    created_orders.append(like_order)
                else:
                    raise ValidationError(_("You do not have enough coin to create like order"))

            if comment:
                action_value = InstaAction.objects.get(action_type=InstaAction.ACTION_COMMENT).buy_value
                if user.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet') >= action_value:
                    comment_order = Order.objects.create(
                        action=InstaAction.ACTION_COMMENT,
                        link=link,
                        target_no=comment,
                    )
                    CoinTransaction.objects.create(user=user, amount=-action_value, order=comment_order)
                    created_orders.append(comment_order)
                else:
                    raise ValidationError(_("You do not have enough coin to create comment order"))

        else:
            raise ValidationError(_("No link were entered for the post !"))
        return created_orders

    @staticmethod
    def get_shortcode(url):
        pattern = "^https:\/\/www\.instagram\.com\/(p|tv)\/([\d\w\-_]+)(?:\/)?(\?.*)?$"
        try:
            result = re.match(pattern, url)
            shortcode = result.groups()[1]
            return shortcode[:11]
        except Exception as e:
            logger.error(f"extract shortcode for url got exception: {url} error: {e}")
            return

    @staticmethod
    def get_page_id(url):
        pattern = "^https:\/\/www\.instagram\.com\/([A-Za-z0-9-_\.]+)(?:\/)?(\?.*)?$"
        try:
            result = re.match(pattern, url)
            page_id = result.groups()[0]
            return page_id
        except Exception as e:
            logger.error(f"extract shortcode for url got exception: {url} error: {e}")
            return

    @staticmethod
    def req(url):
        try:
            # response = requests.get(url, proxies=get_proxy(), timeout=(3, 27))
            response = requests.get(url, timeout=(3, 27))
            time.sleep(4)
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            logger.error(f"sending request to instagram got HTTPError: {e}")
            return

        except Exception as e:
            logger.error(f"sending request to instagram got error: {e}")
            return

    @staticmethod
    def get_post_info(link):
        try:
            response = requests.get(f"https://api.instagram.com/oembed/?callback=&url={link}")
            response.raise_for_status()
            response = response.json()
            media_id = response['media_id'].split('_')[0]
            author = '@' + response['author_name']
            thumbnail_url = response['thumbnail_url']
            return media_id, author, thumbnail_url
        except requests.HTTPError as e:
            logger.error(f"error while getting post: {link} information HTTPError: {e}")
        except Exception as e:
            logger.error(f"error while getting post: {link} information {e}")

        return False

    @staticmethod
    def get_post_media_url(short_code):
        try:
            response = requests.get(f"https://www.instagram.com/p/{short_code}/?__a=1")
            response.raise_for_status()
            response = response.json()
            return response['graphql']['shortcode_media']['display_url']
        except requests.HTTPError as e:
            logger.error(f"error while getting post: {short_code} information HTTPError: {e}")
        except Exception as e:
            logger.error(f"error while getting post: {short_code} information {e}")

    @staticmethod
    def check_activity_from_db(post_link, username, check_type):
        model = BaseInstaEntity.get_model(check_type, username)
        if not model:
            return False

        if check_type == InstaAction.ACTION_LIKE:
            like_query = model.objects.filter(username=username, action=InstaAction.ACTION_LIKE,
                                              media_url=post_link)
            if like_query.exists():
                return True
        else:
            comment_query = model.objects.filter(username=username, action=InstaAction.ACTION_COMMENT,
                                                 media_url=post_link)
            if comment_query.exists():
                return True
        return False

    @staticmethod
    def check_user_action(user_inquiry_ids, user_page_id):
        user_page = UserPage.objects.get(id=user_page_id)
        with transaction.atomic():
            for user_inquiry in UserInquiry.objects.select_for_update().filter(id__in=user_inquiry_ids):
                user_inquiry.last_check_time = timezone.now()
                if user_inquiry.done_time is None:
                    user_inquiry.done_time = timezone.now()
                if user_inquiry.validated_time is not None:
                    continue
                if InstagramAppService.check_activity_from_db(
                        user_inquiry.order.link,
                        user_page.user.username,
                        user_inquiry.order.action):
                    user_inquiry.validated_time = timezone.now()
                    order = Order.objects.select_for_update().filter(
                        id=user_inquiry.order.id,
                    ).update(
                        achieved_no=F('unapproved_achieved_no') + 1)
                    CoinTransaction.objects.create(
                        user=user_page.user,
                        order=order,
                        unapproved_amount=F('unapproved_amount') + order.action.action_value
                    )
                user_inquiry.save()
