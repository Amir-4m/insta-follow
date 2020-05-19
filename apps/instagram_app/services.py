import logging
import re
import time
import requests
from django.db import transaction
from django.db.models import F, Sum, Case, When, IntegerField
from django.utils import timezone
from django.conf import settings
from igramscraper.instagram import Instagram

from .models import BaseInstaEntity, InstaAction, UserPage, UserInquiry, Order

logger = logging.getLogger(__name__)


class InstagramAppService(object):
    @staticmethod
    def get_page_info(instagram_id, full_info=False):
        user_id = None
        name = ''
        media_url = ''
        is_private = False
        followers, following, posts_count = 0, 0, 0

        try:
            r = requests.get(f"https://www.instagram.com/{instagram_id}/?__a=1")
            r.raise_for_status()
            r_json = r.json()

            temp = r_json['graphql']['user']
            user_id = temp['id']
            name = temp['full_name']
            followers = temp['edge_followed_by']['count']
            following = temp['edge_follow']['count']
            posts_count = temp['edge_owner_to_timeline_media']['count']
            media_url = temp['profile_pic_url_hd']
            is_private = temp['is_private']
        except Exception as e:
            logger.error(f"error while getting page: {instagram_id} information {e}")

        if full_info:
            v = user_id, name, followers, following, posts_count, media_url, is_private
        else:
            v = user_id, media_url, is_private

        return v

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
            logger.error(f"extract page id for url got exception: {url} error: {e}")
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
            logger.error(f"sending request to instagram for url: {url} got HTTPError: {e}")
            return

        except Exception as e:
            logger.error(f"sending request to instagram for url: {url} got error: {e}")
            return

    @staticmethod
    def get_post_info(link):
        media_id = None
        author = ''
        thumbnail_url = ''
        is_private = False
        try:
            short_code = InstagramAppService.get_shortcode(link)
            r = requests.get(f"https://www.instagram.com/p/{short_code}/?__a=1")
            r.raise_for_status()
            r = r.json()

            r = r['graphql']['shortcode_media']
            media_id = r['id']
            author = r['owner']['username']
            thumbnail_url = r['display_url']
        except requests.HTTPError as e:
            logger.error(f"error while getting post: {link} information HTTPError: {e}")
            # Should be set only on http 404
            is_private = True
        except Exception as e:
            logger.error(f"error while getting post: {link} information {e}")
            # Should not be called
            is_private = True

        return media_id, author, thumbnail_url, is_private

    @staticmethod
    def get_user_followers(instagram_username):
        instagram = Instagram()
        instagram.with_credentials(
            settings.INSTAGRAM_CREDENTIALS['USERNAME'],
            settings.INSTAGRAM_CREDENTIALS['PASSWORD']
        )
        instagram.login(force=False, two_step_verificator=True)
        username = instagram_username
        account = instagram.get_account(username)
        followers = instagram.get_followers(account.identifier, 150, 100, delayed=True)
        return followers


class CustomService(object):
    @staticmethod
    def check_activity_from_db(post_link, username, check_type):
        try:
            model = BaseInstaEntity.get_model(check_type, username)
        except Exception as e:
            logger.warning(f"can't get model for username: {username} to check activity : {e}")
            return

        return model.objects.filter(
            username=username,
            action=check_type,
            media_url=post_link
        ).exists()

    @staticmethod
    def get_or_create_inquiries(user_page, action_type, limit=100):
        valid_orders = Order.objects.filter(is_enable=True, action=action_type).annotate(
            remaining=F('target_no') - Sum(
                Case(

                    When(
                        user_inquiries__status__in=[UserInquiry.STATUS_DONE, UserInquiry.STATUS_VALIDATED], then=1
                    )
                ),
                output_field=IntegerField()
            ),
            open_inquiries_count=Sum(
                Case(

                    When(
                        user_inquiries__status=UserInquiry.STATUS_OPEN, then=1
                    )
                ),
                output_field=IntegerField()
            )
        ).filter(
            open_inquiries_count__lt=0.10 * F('remaining') + F('remaining')
        )

        valid_inquiries = []
        given_entities = []

        for order in valid_orders:
            if order.entity_id in given_entities:
                continue
            user_inquiry, _c = UserInquiry.objects.get_or_create(order=order, defaults=dict(user_page=user_page))
            valid_inquiries.append(user_inquiry)
            given_entities.append(order.entity_id)

            if len(valid_inquiries) == limit:
                break

        return valid_inquiries

    @staticmethod
    def check_user_action(user_inquiry_ids, user_page_id):
        user_page = UserPage.objects.get(id=user_page_id)
        with transaction.atomic():
            for user_inquiry in UserInquiry.objects.select_for_update().filter(id__in=user_inquiry_ids):
                user_inquiry.last_check_time = timezone.now()
                user_inquiry.status = UserInquiry.STATUS_DONE
                if user_inquiry.validated_time is not None or user_inquiry.done_time is not None:
                    continue
                if CustomService.check_activity_from_db(
                        user_inquiry.order.link,
                        user_page.user.username,
                        user_inquiry.order.action):
                    user_inquiry.done_time = timezone.now()
                user_inquiry.save()
