import json
import logging
import re
import time
import urllib.parse

import requests

from django.db.models import F
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError
from .models import Order, Action
from .endpoints import LIKES_BY_SHORTCODE, COMMENTS_BY_SHORTCODE

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
    def check_user_package_expired(user_package):
        if user_package:
            if (user_package.remaining_follow and user_package.remaining_comment and user_package.remaining_like) == 0:
                user_package.delete()

    @staticmethod
    def create_order(user, follow=None, like=None, comment=None, link=None, page_id=None):
        user_package = user.user_packages.all().last()
        if user_package:
            order_create_list = []
            if follow:
                page_url = 'https://www.instagram.com/%s' % page_id
                follow_order = Order(
                    action_type=Action.FOLLOW,
                    link=page_url,
                    target_no=follow,
                    user_package=user_package,
                )
                if follow_order.user_package.remaining_follow >= follow:
                    follow_order.user_package.remaining_follow -= follow
                    follow_order.user_package.save()
                    order_create_list.append(follow_order)
                else:
                    raise ValidationError(_("Your follow target number should not be more than your package's"))

            if link:
                if like:
                    like_order = Order(
                        action_type=Action.LIKE,
                        link=link,
                        target_no=like,
                        user_package=user_package,
                    )
                    if like_order.user_package.remaining_like >= like:
                        like_order.user_package.remaining_like -= like
                        like_order.user_package.save()
                        order_create_list.append(like_order)
                    else:
                        raise ValidationError(_("Your like target number should not be more than your package's"))

                if comment:
                    comment_order = Order(
                        action_type=Action.COMMENT,
                        link=link,
                        target_no=comment,
                        user_package=user_package,
                    )
                    if comment_order.user_package.remaining_comment >= comment:
                        comment_order.user_package.remaining_comment -= comment
                        comment_order.user_package.save()
                        order_create_list.append(comment_order)
                    else:
                        raise ValidationError(_("Your comment target number should not be more than your package's"))

            else:
                raise ValidationError(_("No link were entered for the post !"))
            objs = Order.objects.bulk_create(order_create_list)
            InstagramAppService.check_user_package_expired(user_package)
            return objs
        else:
            # TODO: change validation errors to non field error
            raise ValidationError(_("You have no active package !"))

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
            page_id = result.groups()[1]
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
    def check_user_action(user_inquiry, user_page):
        link = user_inquiry.order.link
        mode = user_inquiry.order.action_type
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
                            # TODO: async task for creating BaseEntity object for like
                elif mode == Action.COMMENT:
                    for edge in edges:
                        user = edge['node']
                        username = user['owner']['username']
                        text = user['text']
                        if username == user_page.page.instagram_username:
                            found = True
                            # TODO: async task for creating BaseEntity object for comment
                max_id = page_info['end_cursor']
                variables["after"] = max_id
                has_next_page = page_info['has_next_page']

            except Exception as e:
                logger.error(f"got error while getting {link} {mode}s {e}")
                break

        user_inquiry.last_check_time = timezone.now()
        if found:
            user_inquiry.validated_time = timezone.now()
            Order.objects.filter(id=user_inquiry.order.id).update(achieved_no=F('achieved_no') + 1)

        user_inquiry.save()
