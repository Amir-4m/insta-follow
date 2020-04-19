import logging

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from rest_framework.utils import json

User = get_user_model()
logger = logging.getLogger('admood_core.accounts')


class GoogleAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        payload = {'access_token': password}  # validate the token
        r = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', params=payload)
        data = json.loads(r.text)

        if 'error' in data:
            logger.error(data["error"])
            return

        if username != data["email"]:
            logger.error("email is not match")
            return

        try:
            user = User.objects.get(email=data['email'])

        # create user if not exist
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=data["email"],
            )

        return user
