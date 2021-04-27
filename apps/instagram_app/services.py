import json
import logging
import random
import re
import time
from math import ceil

import requests

from django.conf import settings
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, IntegerField, Q, Max, Min
from django.utils import timezone
from django.core.cache import cache

from igramscraper.instagram import Instagram
from Crypto.Cipher import AES
from Crypto import Random
from urllib import parse
from base64 import b64decode, b64encode

from .models import UserInquiry, Order, InstagramAccount

logger = logging.getLogger(__name__)


class InstagramAppService(object):
    @staticmethod
    def api_call(endpoint, method='', data=None, params=None):
        base_url = settings.BASE_API_URL
        url = "%s%s" % (base_url, endpoint)
        try:
            header = {'Authorization': settings.MONITOR_TOKEN}
            if method.lower() == 'get':
                response = requests.get(url=url, headers=header, params=params, timeout=(3.05, 9))
            elif method.lower() == 'post':
                response = requests.post(url=url, headers=header, data=data, timeout=(3.05, 9))
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
    def get_user_followers(session_id, user_id, limit, next_page='', break_point_users=None):

        followers_per_request = 50

        if break_point_users is None:
            break_point_users = []

        count = (ceil(limit / 100) * 100) // followers_per_request

        accounts = []
        for _i in range(count):
            variables = {
                'id': user_id,
                'first': followers_per_request,
                'after': next_page
            }
            endpoint = "https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables=%s"
            url = endpoint % parse.quote_plus(json.dumps(variables, separators=(',', ':')))

            response = requests.get(
                url,
                cookies={'sessionid': session_id},
                headers={'User-Agent': f"{timezone.now().isoformat()}"},
                timeout=(3.05, 9)
            )
            response.raise_for_status()
            result = response.json()['data']['user']['edge_followed_by']
            accounts += [_e['node']['id'] for _e in result['edges']]

            if any(instagram_user_id in accounts for instagram_user_id in break_point_users):
                break

            if result['page_info']['has_next_page']:
                next_page = result['page_info']['end_cursor']
            else:
                break

            # Random wait between 1 and 3 sec to mimic browser
            time.sleep(random.randint(1, 3))

        return accounts

    @staticmethod
    def page_private(instagram_username, session_id):
        url = f'https://www.instagram.com/{instagram_username}/?__a=1'

        try:
            response = requests.get(
                url=url,
                cookies={'sessionid': session_id},
                headers={'User-Agent': f'{timezone.now().isoformat()}'},
                timeout=(3.05, 9)
            )
            response.raise_for_status()
            r_json = response.json()
            result = r_json['graphql']['user']['is_private']

        except KeyError as e:
            logger.warning(f"[page_private check]-[page: {instagram_username}]-[KeyError]-[err: {e}]")
            result = True

        except json.JSONDecodeError:
            logger.warning(f"[page_private check]-[page: {instagram_username}]-[JSONDecodeError]")
            result = None

        except requests.exceptions.HTTPError as e:
            logger.warning(f"[page_private check]-[page: {instagram_username}]-[status code: {e.response.status_code}]")
            result = None
            if e.response.status_code == 404:
                result = True

        except Exception as e:
            logger.error(f"[page_private check]-[page: {instagram_username}]-[{type(e)}]-[err: {e}]")
            result = None

        return result

    @staticmethod
    def get_page_user_id(instagram_username, session_id):
        url = f'https://www.instagram.com/{instagram_username}/?__a=1'
        try:
            response = requests.get(
                url=url,
                cookies={'sessionid': session_id},
                headers={'User-Agent': f'{timezone.now().isoformat()}'},
                timeout=(3.05, 9)
            )
            response.raise_for_status()
            r_json = response.json()
            user_id = r_json['graphql']['user']['id']
        except Exception as e:
            logger.error(f"getting page info failed {instagram_username}: {e}")
            return None
        return user_id


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

        _r = methods[method](f"{settings.PAYMENT_API_URL}{endpoint}/", headers=headers, json=data, timeout=(3.05, 30))
        _r.raise_for_status()
        return _r.json()

    @staticmethod
    def get_or_create_orders(page, action_type, limit=100):

        _is_even = timezone.now().minute % 2
        _iterate_vals = (('gt', 'pk', max), ('lt', '-pk', min))
        _flt, _ord, _fct = _iterate_vals[_is_even]
        _pointer_key = f'order_assign_pointer_{action_type}_{_is_even}'
        _pointer = cache.get(_pointer_key)

        _distinct_orders = list(Order.objects.filter(
            status=Order.STATUS_ENABLE,
            action=action_type
        ).values('entity_id').annotate(min_id=Min('id')).values_list('min_id', flat=True))

        _qs = Order.objects.filter(
            id__in=_distinct_orders
        )

        if _pointer:
            _d = {f'id__{_flt}': _pointer}
            _qs = _qs.filter(**_d)

        orders = list(_qs.annotate(
            remaining=F('target_no') - Coalesce(Sum(
                Case(
                    When(
                        user_inquiries__status=UserInquiry.STATUS_VALIDATED, then=1
                    )
                ),
                output_field=IntegerField()
            ), 0),
        ).filter(
            remaining__gt=0
        ).exclude(
            Q(owner=page) | Q(instagram_username__iexact=page.instagram_username),
        ).exclude(
            entity_id__in=UserInquiry.objects.filter(
                page=page,
                order__action=action_type
            ).values_list('order__entity_id', flat=True)
        ).order_by(_ord)[:limit])

        if len(orders) < limit:
            cache.delete(_pointer_key)
            if _pointer and len(orders) == 0:
                return CustomService.get_or_create_orders(page, action_type, limit)
        else:
            cache.set(_pointer_key, _fct([o.id for o in orders]))

        # result = []
        # for order in orders:
        #     _ck = f"order_{order.id}_assigned"
        #     if order.remaining >= cache.get(_ck, 0):
        #         result.append(order)
        #     cache.add(_ck, 1, 60 * 10)
        #     cache.incr(_ck)
        #
        # return result

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
