import json
import logging
import re
import time
import requests

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from .models import Order, Action, BaseInstaEntity, InstaPage

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
        instagram_page = InstaPage.objects.get(id=page_id)
        if user_package and instagram_page:
            order_create_list = []
            if follow:
                page_url = 'https://www.instagram.com/%s' % instagram_page.instagram_username
                if user_package.remaining_follow >= follow:
                    follow_order = Order.objects.create(
                        action_type=Action.FOLLOW,
                        link=page_url,
                        target_no=follow,
                        user_package=user_package,
                    )
                    follow_order.user_package.remaining_follow -= follow
                    follow_order.user_package.save()
                    order_create_list.append(follow_order)
                else:
                    raise ValidationError(_("Your follow target number should not be more than your package's"))

            if link:
                if like:
                    if user_package.remaining_like >= like:
                        like_order = Order.objects.create(
                            action_type=Action.LIKE,
                            link=link,
                            target_no=like,
                            user_package=user_package,
                        )
                        like_order.user_package.remaining_like -= like
                        like_order.user_package.save()
                        order_create_list.append(like_order)
                    else:
                        raise ValidationError(_("Your like target number should not be more than your package's"))

                if comment:
                    if user_package.remaining_comment >= comment:
                        comment_order = Order.objects.create(
                            action_type=Action.COMMENT,
                            link=link,
                            target_no=comment,
                            user_package=user_package,
                        )
                        comment_order.user_package.remaining_comment -= comment
                        comment_order.user_package.save()
                        order_create_list.append(comment_order)
                    else:
                        raise ValidationError(_("Your comment target number should not be more than your package's"))

            else:
                raise ValidationError(_("No link were entered for the post !"))
            InstagramAppService.check_user_package_expired(user_package)
            return order_create_list
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
    def get_post_info(short_code):
        try:
            response = requests.get(f"https://api.instagram.com/oembed/?callback=&url={short_code}")
            response.raise_for_status()
            response = response.json()
            media_id = response['media_id'].split('_')[0]
            return media_id
        except requests.HTTPError as e:
            logger.error(f"error while getting post: {short_code} information HTTPError: {e}")
        except Exception as e:
            logger.error(f"error while getting post: {short_code} information {e}")

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
        model = BaseInstaEntity.get_model(post_link)
        if not model:
            return False

        if check_type == Action.LIKE:
            like_query = model.objects.filter(username=username, action_type=Action.LIKE)
            if like_query.exists():
                return True
        else:
            comment_query = model.objects.filter(username=username, action_type=Action.COMMENT)
            if comment_query.exists():
                return True
        return False
