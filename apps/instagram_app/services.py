import json
import logging
import requests

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError
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
