import json
import logging
import requests

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .models import Order, Action

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
        user_package = user.user_packages.all().last()
        order_create_list = []
        if follow:
            page_url = 'https://www.instagram.com/%s' % page_id
            order_create_list.append(
                Order(
                    action_type=Action.FOLLOW,
                    link=page_url,
                    target_no=follow,
                    user_package=user_package,
                )
            )

        if link:
            if like:
                order_create_list.append(
                    Order(
                        action_type=Action.LIKE,
                        link=link,
                        target_no=like,
                        user_package=user_package,
                    )

                )

            if comment:
                order_create_list.append(
                    Order(
                        action_type=Action.COMMENT,
                        link=link,
                        target_no=comment,
                        user_package=user_package,
                    )
                )

        else:
            raise ValidationError(_("No link were entered for the post !"))
        return Order.objects.bulk_create(order_create_list)
