import json
import logging
import random
import re
import time

import requests

from django.conf import settings
from django.core.cache import cache
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, IntegerField, Q
from django.utils import timezone

from igramscraper.instagram import Instagram
from Crypto.Cipher import AES
from Crypto import Random
from urllib import parse
from base64 import b64decode, b64encode

from .models import UserInquiry, Order, InstagramAccount, AllowedGateway

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
                logger.critical(f"no instagram account found")
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
                logger.critical(f"logging in to instagram with account {instagram_account.username} got error: {e}")
        raise Exception("instagram login reached max retries !")

    @staticmethod
    def get_user_followers(session_id, user_id, count=settings.FOLLOWER_LIMIT, end_cursor='', delayed=True):
        next_page = end_cursor
        accounts = []
        for _i in range(count):
            variables = {
                'id': user_id,
                'first': str(count),
                'after': next_page
            }
            endpoint = "https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables=%s"
            url = endpoint % parse.quote_plus(json.dumps(variables, separators=(',', ':')))

            response = requests.get(
                url,
                cookies={'sessionid': session_id},
                headers={'User-Agent': f"{timezone.now().isoformat()}"})

            response.raise_for_status()
            result = response.json()['data']['user']['edge_followed_by']

            accounts += [_e['node']['username'] for _e in result['edges']]

            if result['page_info']['has_next_page']:
                next_page = result['page_info']['end_cursor']
            else:
                break

            if delayed:
                # Random wait between 1 and 3 sec to mimic browser
                microsec = random.uniform(2.0, 6.0)
                time.sleep(microsec)

        return accounts


class CustomService(object):

    @staticmethod
    def payment_request(endpoint, method, data=None):
        headers = {
            "Authorization": f"TOKEN {settings.PAYMENT_SERVICE_SECRET}",
            "Content-Type": "application/json"
        }
        methods = {
            'get': requests.get,
            'post': requests.post
        }

        response = methods[method](f"{settings.PAYMENT_API_URL}{endpoint}/", headers=headers, json=data)
        response.raise_for_status()
        return response

    @staticmethod
    def get_or_create_orders(page, action_type, limit=100):
        orders = Order.objects.filter(is_enable=True, action=action_type).annotate(
            remaining=F('target_no') - Coalesce(Sum(
                Case(
                    When(
                        user_inquiries__status=UserInquiry.STATUS_VALIDATED, then=1
                    )
                ),
                output_field=IntegerField()
            ), 0),
        ).filter(
            remaining__lte=F('remaining')
        ).exclude(
            Q(owner=page) | Q(instagram_username__iexact=page.instagram_username),

        ).exclude(
            entity_id__in=UserInquiry.objects.filter(page=page, order__action=action_type).values_list(
                'order__entity_id', flat=True
            )
        )[:limit]

        return orders


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


class GatewayService(object):
    @staticmethod
    def get_gateways_by_version_name(version_name):
        gateways = cache.get("gateways")
        allowed_gateways = []
        for gw in AllowedGateway.objects.all():
            if re.match(gw.version_pattern, version_name) is not None:
                allowed_gateways = gw.gateways_code
                break

        for gateway in gateways:
            if gateway['code'] in allowed_gateways:
                yield gateway
