import logging

from django.db.models import Sum
from django.test import override_settings
from django.urls import reverse
from django.test.client import RequestFactory

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient

from apps.accounts.models import User
from apps.instagram_app.models import UserPage, CoinTransaction, InstaAction, Order, UserInquiry
from apps.instagram_app.api.serializers import ProfileSerializer, OrderSerializer, UserInquirySerializer, \
    DeviceSerializer


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class InstagramAPITestCase(APITestCase):
    fixtures = ['instagram']

    def setUp(self):
        self.user = User.objects.get(id=1)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_get_profile(self):
        url = reverse('profile-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('id'), self.user.id)

    def test_post_profile(self):
        url = reverse('profile-list')
        data = {
            'instagram_username': 'hello_world',
        }
        response = self.client.post(url, data=data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserPage.objects.filter(
            page__instagram_username=data['instagram_username'],
            user=self.user
        ).exists()
                        )

    def test_delete_profile(self):
        url = reverse('profile-detail', kwargs={'pk': 1})
        response = self.client.delete(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserPage.objects.get(pk=1).is_active)

    def test_get_order(self):
        url = reverse('order-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_order(self):
        url = reverse('order-list')
        CoinTransaction(user=self.user, amount=20)
        data = {
            'action': 'L',
            'link': 'http://instagram.com/',
            'target_no': 1
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Order.objects.filter(action=data['action'], link=data['link'], target_no=data['target_no']).exists()
        )

    def test_recheck_order_not_enable(self):
        url = reverse('order-recheck', kwargs={'pk': 5})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recheck_order_enable(self):
        url = reverse('order-recheck', kwargs={'pk': 4})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_inquiry_comment(self):
        url = reverse('userinquiry-comment')
        response = self.client.get(url, {'page_id': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_inquiry_comment_duplicate_order(self):
        url = reverse('userinquiry-comment')
        response = self.client.get(url, {'page_id': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_inquiry_like(self):
        url = reverse('userinquiry-like')
        response = self.client.get(url, {'page_id': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_inquiry_follow(self):
        url = reverse('userinquiry-follow')
        response = self.client.get(url, {'page_id': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_inquiry_no_page_id(self):
        url = reverse('userinquiry-like')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'Error': 'page_id is required'})

    def test_get_user_inquiry_invalid_page(self):
        url = reverse('userinquiry-like')
        response = self.client.get(url, {'page_id': 10}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRaisesMessage(ValidationError, {'Error': 'user and page does not match!'})

    def test_post_user_inquiry(self):
        url = reverse('userinquiry-done')
        data = {
            'done_ids': [1],
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserInquiry.objects.filter(id=1, status=UserInquiry.STATUS_DONE))

    def test_get_coin_transaction(self):
        url = reverse('cointransaction-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_coin_transaction_total(self):
        url = reverse('cointransaction-total')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['wallet'],
            self.user.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet') or 0
        )

    def test_post_device_id(self):
        url = reverse('device-list')
        data = {
            'device_id': 2,
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class InstagramSerializerTestCase(APITestCase):
    fixtures = ['instagram']

    def setUp(self):
        self.user = User.objects.get(id=1)
        self.request = RequestFactory()
        self.request.user = self.user
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_profile_serializer(self):
        data = {
            'instagram_username': 'hello_world',
            'user_id': 123456
        }
        serializer = ProfileSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_insta_page_not_active(self):
        data = {
            "instagram_username": 'test3',
            "user_id": 12312378
        }
        serializer = ProfileSerializer(data=data, context={'user': self.user})
        user_page = UserPage.objects.get(page__instagram_user_id=12312378)

        self.assertTrue(serializer.is_valid())
        serializer.save()
        user_page.refresh_from_db()
        self.assertTrue(user_page.is_active)

    def test_order_serializer_valid_lc_data(self):
        data = {
            "action": InstaAction(pk=InstaAction.ACTION_LIKE),
            "target_no": 70,
            "link": "http://127.0.0.1:8000/api/v1/instagram/orders/"
        }
        serializer = OrderSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_order_serializer_invalid_lc_data(self):
        data = {
            "action": InstaAction(pk=InstaAction.ACTION_LIKE),
            "target_no": 70,
        }
        serializer = OrderSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertRaisesMessage(
            ValidationError,
            'link field is required for like and comment !',
            serializer.validate,
            data
        )

    def test_order_serializer_invalid_follow_data(self):
        data = {
            "action": InstaAction(pk=InstaAction.ACTION_FOLLOW),
            "target_no": 70,
        }
        serializer = OrderSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertRaisesMessage(
            ValidationError,
            'instagram_username field is required for follow!',
            serializer.validate,
            data
        )

    def test_order_serializer_create_follow_invalid_coin(self):
        data = {
            "action": InstaAction(pk=InstaAction.ACTION_FOLLOW),
            "target_no": 70,
            "link": None,
            "instagram_username": "test"
        }
        serializer = OrderSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertRaisesMessage(
            ValidationError,
            'You do not have enough coin to create order',
            serializer.save,
            user=self.user
        )

    def test_order_serializer_create_follow_valid_coin(self):
        data = {
            "action": InstaAction(pk=InstaAction.ACTION_FOLLOW),
            "target_no": 1,
            'link': None,
            "instagram_username": "test"
        }
        CoinTransaction.objects.create(user=self.user, amount=100)
        serializer = OrderSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save(user=self.user)
        self.assertEqual(self.user.user_orders.last().id, serializer.data['id'])

    def test_user_inquiry_valid_data(self):
        data = {
            'done_ids': [1],
        }
        serializer = UserInquirySerializer(data=data, context={'request': self.request})
        self.assertTrue(serializer.is_valid())

    # def test_user_inquiry_invalid_inquiry_data(self):
    #     data = {
    #         'done_ids': [8],
    #     }
    #     serializer = UserInquirySerializer(data=data, context={'request': self.request})
    #     self.assertFalse(serializer.is_valid())
    #     self.assertRaisesMessage(
    #         ParseError,
    #         'list is not valid!',
    #         serializer.validate,
    #         data
    #     )

    def test_device_id_create(self):
        data = {
            "device_id": '1'
        }
        serializer = DeviceSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save(user=self.user)
        self.assertEqual(self.user.devices.last().device_id, serializer.data['device_id'])
