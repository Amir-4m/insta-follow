import logging
import re
import requests
from django.conf import settings
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, IntegerField
from igramscraper.instagram import Instagram

from .models import InstaAction, UserInquiry, Order, InstagramAccount

logger = logging.getLogger(__name__)


class InstagramAppService(object):
    @staticmethod
    def api_call(endpoint, method='', data=None, params=None):
        base_url = settings.BASE_API_URL
        url = "%s%s" % (base_url, endpoint)
        try:
            header = {'Authorization': settings.MONITOR_TOKEN}
            if method.lower() == 'get':
                response = requests.get(url=url, headers=header, params=params)
            elif method.lower() == 'post':
                response = requests.post(url=url, headers=header, data=data)
            else:
                return None
            return response
        except Exception as e:
            logger.error(f'{method} api call {endpoint} got error: {e}')
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
                instagram.login()
                return instagram

            except Exception as e:
                instagram_account.is_enable = False
                instagram_account.save()
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
    def check_activity_from_db(inquiry_user_id, order_track_id, check_type):
        endpoint = "monitor/orders/%s/user_action/" % order_track_id
        params = {"user_id": inquiry_user_id}
        response = InstagramAppService.api_call(endpoint, method='get', params=params)
        response.raise_for_status()
        response_json = response.json()
        if check_type == InstaAction.ACTION_COMMENT and response_json.get('commented') is not None:
            is_done = response_json.get('commented')
        elif check_type == InstaAction.ACTION_FOLLOW and response_json.get('followed') is not None:
            is_done = response_json.get('followed')
        elif check_type == InstaAction.ACTION_LIKE and response_json.get('liked') is not None:
            is_done = response_json.get('liked')
        else:
            return False
        return is_done

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
