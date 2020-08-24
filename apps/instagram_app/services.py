import hashlib
import logging
import re
import requests

from django.conf import settings
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, IntegerField

from igramscraper.instagram import Instagram
from Crypto.Cipher import AES
from Crypto import Random
from base64 import b64decode, b64encode

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
    def get_or_create_inquiries(page, action_type, limit=100):
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
                page=page,
                defaults=dict(page=page)
            )
            if user_inquiry and _c:
                valid_inquiries.append(user_inquiry)
                given_entities.append(order.entity_id)

            if len(valid_inquiries) == limit:
                break

        return valid_inquiries


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

    @staticmethod
    def mongo_exists(collection, **kwargs):
        try:
            return bool(collection.objects.mongo_find_one(dict(kwargs)))
        except Exception as e:
            logger.error(f"error in mongo filter occurred :{e}")


class CryptoService:

    def __init__(self, key):
        """
        Requires string param as a key
        """
        self.key = key
        self.BS = AES.block_size

    def __pad(self, s):
        return s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)

    @staticmethod
    def __unpad(s):
        return s[0:-ord(s[-1])]

    def encrypt(self, raw):
        """
        Returns b64encode encoded encrypted value!
        """
        raw = self.__pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        """
        Requires b64encode encoded param to decrypt
        """
        enc = b64decode(enc)
        iv = enc[:16]
        enc = enc[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self.__unpad(cipher.decrypt(enc).decode())
