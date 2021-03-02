import json
import logging
import random
import string

from django.utils.encoding import smart_text
from psycopg2._psycopg import IntegrityError

from apps.instagram_app.api.serializers import InstaActionSerializer
from apps.instagram_app.services import CryptoService
from datetime import datetime, timedelta
from django.db.models import Sum
from django.test import override_settings
from django.urls import reverse
from django.test.client import RequestFactory

from rest_framework import status, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient

# Testcases for Order and UserInquiry
from apps.instagram_app.models import InstaPage, Order, InstaAction, UserInquiry, CoinTransaction


# creating some serializers for test cases
class InstaPageTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = '__all__'


class OrderTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'


class BaseAuthenticatedTestCase(APITestCase):
    def setUp(self):
        try:
            self.page = InstaPage.objects.get(instagram_username="instagram_username")
        except InstaPage.DoesNotExist:
            self.page = InstaPage.objects.create(
                instagram_username="instagram_username",
                instagram_user_id=111222333444,
                session_id="test-session"
            )
        # randomly select an order
        self.orders = dict()

        self.disable_order = None
        self.complete_order = None

        if Order.objects.filter(status=Order.STATUS_ENABLE).count() > 1:
            self.orders[Order.STATUS_ENABLE] = random.choice(Order.objects.filter(status=Order.STATUS_ENABLE))
        else:
            # first try to get a random InstaAction
            insta_action = InstaAction.objects.create(
                action_type=random.choice([InstaAction.ACTION_LIKE,
                                           InstaAction.ACTION_FOLLOW,
                                           InstaAction.ACTION_COMMENT]),
                action_value=10,
                buy_value=200
            )
            self.orders[Order.STATUS_ENABLE] = Order.objects.create(
                action=insta_action,
                # one hundred like, follow or comment request
                target_no=100,
                link="https://instagram.com/some-random-hash/",
                media_properties={
                    'video_address': 'some_video_address',
                },
                entity_id=random.randint(10000, 88888888),
                instagram_username="some-username",
                comments=[
                    f"comment 1 {''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}",
                    f"comment 2 {''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}",
                    f"comment 3 {''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}",
                ],
                description="Some description",
                status=Order.STATUS_ENABLE,
                is_enable=True,
                owner=self.page
            )

        self.request = RequestFactory()
        self.request.user = self.page
        # generate a token for authentication
        dt = datetime.utcnow()
        self.token = CryptoService(dt.strftime("%d%m%y%H") + dt.strftime("%d%m%y%H")).encrypt(str(self.page.uuid))
        # Authenticate the client :
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + smart_text(self.token))

        self.register_order_data = {
            'entity_id': random.randint(200, 1000),
            'page': self.page.id,
            'action': None,
            'target_no': 10,
            'comments': ['comment 1', 'comment 2', 'comment 3'],
            'instagram_username': 'some_username',
            'link': 'https//instagram.com/link/',
            'media_properties': {
                'link': 'https//instagram.com/link/'
            },
            # this is necessary for all actions except InstaAction.ACTION_COMMENT and LIKE
            'shortcode': '65asvxav',
        }
        logging.disable(logging.CRITICAL)


class UserInquiryTestCases(BaseAuthenticatedTestCase):
    # fixtures = ['instagram']

    def setUp(self):
        super(UserInquiryTestCases, self).setUp()

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_eo_inquiries_page_user_condition_and_done(self):
        """
            Consider that eo stands for enable orders
        """
        url = reverse('userinquiry-list')
        data = {
            'page': self.page.id,
            'order': self.orders[Order.STATUS_ENABLE].id,
            'status': UserInquiry.STATUS_VALIDATED,
            'earned_coin': '50',
            'check': False
        }

        response = self.client.post(url, data=data, format='json')
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_inquiry = UserInquiry.objects.get(order=self.orders[Order.STATUS_ENABLE], page=self.page)
        self.assertEqual(user_inquiry.status, UserInquiry.STATUS_VALIDATED)
        # the list of orders are filtered before so checking this condition is not necessary
        # self.assertNotEqual(user_inquiry.page.id, self.orders[Order.STATUS_ENABLE].owner.id)
        # check that an inquiry operation should not be done twice
        second_response = self.client.post(url, data=data, format='json')
        self.assertIn('order with this id already has been done by this page!', smart_text(second_response.content))

        # this scenario should give an error status not correct
        data = {
            'page': self.page.id,
            'order': self.orders[Order.STATUS_ENABLE].id,
            'status': UserInquiry.STATUS_CHOICES,
            'earned_coin': '50',
            'check': False
        }
        third_response = self.client.post(url, data=data, format='json')
        self.assertIn('is not a valid choice', smart_text(third_response.content))

    def test_inquiries_done(self):
        url = reverse('userinquiry-done')
        data = {
            'order': self.orders[Order.STATUS_ENABLE].id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OrderTestCases(BaseAuthenticatedTestCase):
    # fixtures = ['instagram']

    def setUp(self):
        super(OrderTestCases, self).setUp()

    def test_orders_get(self):
        url = reverse('order-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_orders_post(self):
        url = reverse('order-list')
        CoinTransaction.objects.create(page=self.page, amount=50)
        action_type = random.choice([
            InstaAction.ACTION_LIKE,
            InstaAction.ACTION_FOLLOW,
            InstaAction.ACTION_COMMENT
        ])
        instagram_action, created = InstaAction.objects.get_or_create(
            # action type is considered as primary key in this table
            action_type=action_type,
            action_value=2,
            buy_value=2
        )
        self.register_order_data['action'] = instagram_action.action_type
        response = self.client.post(url, data=self.register_order_data, format='json')
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # the link is changed based on action type so if put it here result in test failure
        self.assertTrue(
            Order.objects.filter(action=instagram_action,
                                 target_no=self.register_order_data['target_no']).count() > 0
        )

    def test_orders_post_action_code_for_like_follow(self):
        url = reverse('order-list')
        CoinTransaction.objects.create(page=self.page, amount=50)
        action_type = random.choice([
            InstaAction.ACTION_LIKE,
            InstaAction.ACTION_COMMENT,
        ])
        instagram_action, created = InstaAction.objects.get_or_create(
            # action type is considered as primary key in this table
            action_type=action_type,
            action_value=2,
            buy_value=2
        )
        # override actions because it is different in some scenarios
        self.register_order_data['action'] = instagram_action.action_type
        del self.register_order_data['shortcode']
        response = self.client.post(url, data=self.register_order_data, format='json')
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_orders_post_action_follow_no_username(self):
        url = reverse('order-list')
        CoinTransaction.objects.create(page=self.page, amount=50)
        action_type = InstaAction.ACTION_FOLLOW

        instagram_action, created = InstaAction.objects.get_or_create(
            # action type is considered as primary key in this table
            action_type=action_type,
            action_value=2,
            buy_value=2
        )
        self.register_order_data['action'] = instagram_action.action_type
        del self.register_order_data['instagram_username']
        response = self.client.post(url, data=self.register_order_data, format='json')
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_orders_post_comments_none_like_follow(self):
        url = reverse('order-list')
        CoinTransaction.objects.create(page=self.page, amount=50)
        action_type = random.choice([
            InstaAction.ACTION_FOLLOW,
            InstaAction.ACTION_LIKE,
        ])

        instagram_action, created = InstaAction.objects.get_or_create(
            # action type is considered as primary key in this table
            action_type=action_type,
            action_value=2,
            buy_value=2
        )
        self.register_order_data['action'] = instagram_action.action_type
        response = self.client.post(url, data=self.register_order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.exclude(id=self.orders[Order.STATUS_ENABLE].id).first()
        self.assertEqual(order.comments, None)

    def test_orders_post_previous_order_target_no_increase(self):
        url = reverse('order-list')
        CoinTransaction.objects.create(page=self.page, amount=50)
        action_type = random.choice([
            InstaAction.ACTION_FOLLOW,
            InstaAction.ACTION_LIKE,
        ])

        instagram_action, created = InstaAction.objects.get_or_create(
            # action type is considered as primary key in this table
            action_type=action_type,
            action_value=2,
            buy_value=2
        )
        self.register_order_data['action'] = instagram_action.action_type
        target_no = 10
        response = self.client.post(url, data=self.register_order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(url, data=self.register_order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.exclude(id=self.orders[Order.STATUS_ENABLE].id).first()
        self.assertEqual(order.target_no, target_no * 2)

    # def test_orders_comments_get(self):
    #     url = reverse('order-comment')
    #     create_url = reverse('order-list')
    #     response = self.client.post(create_url, data=self.register_order_data, format='json')
    #     print(Order.objects.first())
    #     response = self.client.get(url, format='json')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
