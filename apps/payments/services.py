import json
import os

from django.core.cache import caches
from django.conf import settings

import requests


class BazaarService(object):
    @staticmethod
    def get_access_token():
        cache = caches['payments']
        access_code = cache.get('bazaar_access_code')
        endpoint = 'https://pardakht.cafebazaar.ir/devapi/v2/auth/token/'
        if access_code is None and not os.path.isfile(f"{settings.BASE_DIR}/apps/payments/token/token.txt"):
            data = {
                "grant_type": "authorization_code",
                "code": settings.BAZAAR_AUTH_CODE,
                "redirect_uri": settings.BAZAAR_REDIRECT_URI,
                "client_id": settings.BAZAAR_CLIENT_ID,
                "client_secret": settings.BAZAAR_CLIENT_SECRET
            }
            response = requests.post(endpoint, data=data)
            response.raise_for_status()
            res_json = response.json()
            access_code = res_json.get('access_token')
            cache.set('bazaar_access_code', access_code)
            with open(f"{settings.BASE_DIR}/apps/payments/token/token.txt", 'w') as token_file:
                json.dump(res_json, token_file)
            return access_code
        elif access_code is None and os.path.isfile(f"{settings.BASE_DIR}/apps/payments/token/token.txt"):
            with open(f"{settings.BASE_DIR}/apps/payments/token/token.txt") as json_file:
                refresh_token = json.load(json_file).get('refresh_token')
            data = {
                "grant_type": "refresh_token",
                "client_id": settings.BAZAAR_CLIENT_ID,
                "client_secret": settings.BAZAAR_CLIENT_SECRET,
                "refresh_token": refresh_token
            }
            response = requests.post(endpoint, data=data)
            response.raise_for_status()
            res_json = response.json()
            access_code = res_json.get('access_token')
            cache.set('bazaar_access_code', access_code)
            return access_code
        else:
            return access_code

    @staticmethod
    def verify_purchase(package_name, product_id, purchase_token):
        iab_base_api = "https://pardakht.cafebazaar.ir/devapi/v2/api"
        iab_api_path = "validate/{}/inapp/{}/purchases/{}/".format(
            package_name,
            product_id,
            purchase_token
        )
        iab_url = "{}/{}".format(iab_base_api, iab_api_path)
        access_token = BazaarService.get_access_token()
        headers = {'Authorization': access_token}
        response = requests.get(iab_url, headers=headers)
        if response.status_code == 200:
            return True
        return False
