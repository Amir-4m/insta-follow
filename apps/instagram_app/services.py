import logging
import re
import time
import requests
from django.conf import settings
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, IntegerField
from igramscraper.instagram import Instagram

from .models import BaseInstaEntity, UserInquiry, Order, InstagramAccount

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
            instagram = InstagramAppService.instagram_login()
            r = requests.get(
                url=f"https://www.instagram.com/{instagram_id}/?__a=1",
                headers=instagram.generate_headers(instagram.user_session)
            )
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
            instagram = InstagramAppService.instagram_login()
            short_code = InstagramAppService.get_shortcode(link)
            r = requests.get(
                f"https://www.instagram.com/p/{short_code}/?__a=1",
                headers=instagram.generate_headers(instagram.user_session)
            )
            r.raise_for_status()
            r_json = r.json()

            temp = r_json['graphql']['shortcode_media']
            media_id = temp['id']
            author = temp['owner']['username']
            thumbnail_url = temp['display_url']
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
    def instagram_login():
        max_retries = 3
        tries = 0

        while tries < max_retries:
            tries += 1

            instagram_account = InstagramAccount.objects.filter(is_enable=True).order_by('login_attempt').first()
            if instagram_account is None:
                logger.error(f"no instagram account found")
                return
            instagram_account.login_attempt += 1
            instagram_account.save()
            instagram = Instagram()
            instagram.with_credentials(
                instagram_account.username,
                instagram_account.password
            )
            try:
                instagram.login(two_step_verificator=True)
                return instagram

            except Exception as e:
                logger.error(f"logging in to instagram with account {instagram_account.username} got error: {e}")
        raise Exception("instagram login reached max retries !")

    @staticmethod
    def get_user_followers(instagram_username):
        instagram = InstagramAppService.instagram_login()
        username = instagram_username
        account = instagram.get_account(username)
        followers = instagram.get_followers(account.identifier, settings.FOLLOWER_LIMIT, 100, delayed=True)
        return followers


class CustomService(object):
    @staticmethod
    def check_activity_from_db(inquiry_user_id, order_entity_id, check_type):
        try:
            model = BaseInstaEntity.get_model(check_type, order_entity_id)
        except Exception as e:
            logger.warning(f"can't get model for username: {order_entity_id} to check activity : {e}")
            return

        return CustomService.mongo_exists(
            model,
            user_id=str(inquiry_user_id),
            action=check_type,
        )

    @staticmethod
    def get_or_create_inquiries(user_page, action_type, limit=100):
        valid_orders = Order.objects.filter(is_enable=True, action=action_type).annotate(
            remaining=F('target_no') - Coalesce(Sum(
                Case(
                    When(
                        user_inquiries__status__in=[UserInquiry.STATUS_DONE, UserInquiry.STATUS_VALIDATED], then=1
                    )
                ),
                output_field=IntegerField()
            ), 0),
            open_inquiries_count=Coalesce(Sum(
                Case(

                    When(
                        user_inquiries__status=UserInquiry.STATUS_OPEN, then=1
                    )
                ),
                output_field=IntegerField()
            ), 0)
        ).filter(
            open_inquiries_count__lt=0.10 * F('remaining') + F('remaining')
        )
        valid_inquiries = []
        given_entities = []

        for order in valid_orders:
            if order.entity_id in given_entities:
                continue

            user_inquiry, _c = UserInquiry.objects.get_or_create(
                order=order,
                user_page=user_page,
                defaults=dict(user_page=user_page)
            )
            if user_inquiry and _c:
                valid_inquiries.append(user_inquiry)
                given_entities.append(order.entity_id)

            if len(valid_inquiries) == limit:
                break

        return valid_inquiries

    @staticmethod
    def mongo_exists(collection, **kwargs):
        try:
            return bool(collection.objects.mongo_find_one(dict(kwargs)))
        except Exception as e:
            logger.error(f"error in mongo filter occurred :{e}")


class MongoServices(object):
    @staticmethod
    def get_object_id(collection, **kwargs):
        try:
            obj = collection.objects.mongo_find_one(dict(kwargs))
            return obj.get("_id")
        except Exception as e:
            logger.error(f"error in mongo get object id :{e}")

    @staticmethod
    def get_object_position(collection, object_id):
        return collection.objects.mongo_find(
            {
                "_id": {
                    "$lt": object_id
                },
            }
        ).sort([("$natural", -1)]).count() + 1

    @staticmethod
    def get_object_neighbors(collection, object_id, limit=20):
        top_neighbors = collection.objects.mongo_find(
            {
                "_id": {
                    "$gt": object_id
                },
            }
        ).sort([("$natural", -1)]).limit(limit)

        bottom_neighbors = collection.objects.mongo_find(
            {
                "_id": {
                    "$lt": object_id
                },
            }
        ).sort([("$natural", -1)]).limit(limit)

        return top_neighbors, bottom_neighbors
