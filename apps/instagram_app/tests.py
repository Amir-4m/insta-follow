from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.accounts.models import User
from apps.instagram_app.models import UserPage


class InstagramAPITestCase(APITestCase):
    fixtures = ['instagram']

    def setUp(self):
        self.user = User(id=1)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        url = reverse('profile-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('id'), self.user.id)

    def test_post_profile(self):
        url = reverse('profile-list')
        data = {
            'instagram_username': 'hello_world',
            'user_id': 123456
        }
        response = self.client.post(url, data=data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserPage.objects.get(
            page__instagram_username=data['instagram_username'],
            page__instagram_user_id=data['user_id'],
            user=self.user
        )
        )