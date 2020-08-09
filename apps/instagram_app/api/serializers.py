import logging
import random
import requests
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, ParseError

from apps.instagram_app.models import (
    UserInquiry, CoinTransaction, Order,
    InstaAction, Device, CoinPackage,
    CoinPackageOrder, InstaPage, Comment
)

logger = logging.getLogger(__name__)


class LoginVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = ('instagram_user_id', 'instagram_username', 'session_id', 'uuid')
        read_only_fields = ('uuid',)

    def validate(self, attrs):
        username = attrs['instagram_username']
        user_id = attrs['instagram_user_id']
        session_id = attrs['session_id']
        user_agent = "Instagram 10.15.0 Android (28/9; 411dpi; 1080x2220; samsung; SM-A650G; SM-A650G; Snapdragon 450; en_US)"
        try:

            response = requests.get(
                url=f'https://i.instagram.com/api/v1/users/{user_id}/info/',
                cookies={'sessionid': session_id},
                headers={'User-Agent': user_agent}
            )
            temp = response.json()['user']

            if (temp['pk'] != str(user_id) or temp['username'] != username) or temp.get('account_type') is None:
                raise ValidationError(
                    detail={'detail': _('invalid credentials provided!')}
                )

        except Exception as e:
            logger.error(f"error in login verification for user id {user_id}: {e}")
            raise ValidationError(
                detail={'detail': _('error occurred while logging in!')}
            )
        return attrs

    def create(self, validated_data):
        username = validated_data['instagram_username']
        user_id = validated_data['instagram_user_id']
        session_id = validated_data['session_id']

        page, created = InstaPage.objects.get_or_create(
            instagram_user_id=user_id,
            defaults={
                "instagram_username": username,
                "session_id": session_id
            }
        )
        return page


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('device_id',)

    def create(self, validated_data):
        page = validated_data.get('page')
        device_id = validated_data.get('device_id')
        return Device.objects.create(page=page, device_id=device_id)


# class InstaPagesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = InstaPage
#         fields = ('id', 'instagram_username', 'instagram_user_id')


# class ProfileSerializer(serializers.ModelSerializer):
#     insta_pages = serializers.SerializerMethodField(read_only=True)
#     approved_wallet = serializers.SerializerMethodField(read_only=True)
#     unapproved_wallet = serializers.SerializerMethodField(read_only=True)
#     instagram_username = serializers.CharField(write_only=True)
#
#     class Meta:
#         model = User
#         fields = ('id', 'insta_pages', 'approved_wallet', 'unapproved_wallet', 'instagram_username')
#         read_only_fields = ('id',)
#
#     def get_approved_wallet(self, obj):
#         return obj.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0))['wallet']
#
#     def get_unapproved_wallet(self, obj):
#         return UserInquiry.objects.filter(
#             user_page__user=obj,
#             status=UserInquiry.STATUS_DONE,
#         ).aggregate(coins=Coalesce(Sum('order__action__action_value'), 0))['coins']
#
#     def get_insta_pages(self, obj):
#         qs = obj.insta_pages.filter(user_pages__is_active=True)
#         return InstaPagesSerializer(qs, many=True).data
#
#     def create(self, validated_data):
#         page_id = validated_data.get('instagram_username')
#         user = self.context['user']
#         page, created = InstaPage.objects.get_or_create(
#             instagram_username=page_id,
#         )
#         UserPage.objects.update_or_create(
#             user=user,
#             page=page,
#             defaults={
#                 'is_active': True
#             }
#         )
#         return user


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'id', 'entity_id', 'action',
            'target_no', 'achieved_number_approved', 'link',
            'instagram_username', 'is_enable', 'description',
            'media_url', 'comments'
        )
        read_only_fields = ('is_enable', 'achieved_number_approved', 'description')
        extra_kwargs = {
            'link': {'allow_null': True, 'required': False, 'allow_blank': True}
        }

    def validate(self, attrs):
        action_value = attrs.get('action')
        link = attrs.get('link')
        instagram_username = attrs.get('instagram_username')
        comments = attrs.get('comments')
        if action_value.pk in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT] and not link:
            raise ValidationError(detail={'detail': _('link field is required for like and comment !')})
        if action_value.pk == InstaAction.ACTION_FOLLOW and not instagram_username:
            raise ValidationError(
                detail={'detail': _('instagram_username field is required for follow!')})
        if action_value.pk in [InstaAction.ACTION_LIKE, InstaAction.ACTION_FOLLOW] and comments is not None:
            raise ValidationError(detail={'detail': _('comment is not allowed in like and follow methods!')})
        return attrs

    def create(self, validated_data):
        entity_id = validated_data.get('entity_id')
        page = validated_data.get('page')
        insta_action = validated_data.get('action')
        target_no = validated_data.get('target_no')
        link = validated_data.get('link')
        comments = validated_data.get('comments')
        if insta_action.pk == InstaAction.ACTION_FOLLOW:
            instagram_username = validated_data.get('instagram_username')
            link = f"https://www.instagram.com/{instagram_username}/"

        with transaction.atomic():
            page = InstaPage.objects.select_for_update().get(id=page.id)
            if page.coin_transactions.all().aggregate(
                    wallet=Coalesce(Sum('amount'), 0)
            )['wallet'] < insta_action.buy_value * target_no:
                raise ValidationError(detail={'detail': _("You do not have enough coin to create order")})

            ct = CoinTransaction.objects.create(page=page, amount=-(insta_action.buy_value * target_no))
            order = Order.objects.create(
                entity_id=entity_id,
                action=insta_action,
                link=link,
                target_no=target_no,
                owner=page,
                comments=comments
            )
            ct.order = order
            ct.description = f"create order {order.id}"
            ct.save()
            return order


class UserInquirySerializer(serializers.ModelSerializer):
    link = serializers.ReadOnlyField(source="order.link")
    media_url = serializers.ReadOnlyField(source="order.media_url")
    instagram_username = serializers.ReadOnlyField(source='order.instagram_username')
    page = serializers.ReadOnlyField(source='page.instagram_username')
    action = serializers.ReadOnlyField(source='order.action.action_type')
    comment = serializers.SerializerMethodField()
    done_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    class Meta:
        model = UserInquiry
        fields = ('id', 'link', 'instagram_username', 'media_url', 'done_ids', 'status', 'page', 'action', 'comment')

    def validate_done_ids(self, value):
        page = self.context['request'].auth['page']
        id_list = UserInquiry.objects.filter(
            id__in=value, page=page, status=UserInquiry.STATUS_OPEN
        ).values_list('id', flat=True)
        if not id_list:
            raise ParseError(_('list is not valid!'))
        return value

    def get_comment(self, obj):
        if obj.order.action.action_type == InstaAction.ACTION_COMMENT:
            comments = obj.order.comments
            return random.choice(comments)
        return None


class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinTransaction
        exclude = ('page',)


class InstaActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaAction
        fields = ('action_type', 'action_value', 'buy_value')


class CoinPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPackage
        fields = ('name', 'product_id', 'amount', 'price', 'is_enable')


class CoinPackageOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPackageOrder
        fields = ('invoice_number', 'coin_package', 'page', 'purchase_token', 'is_paid', 'price')


class PurchaseSerializer(serializers.Serializer):
    invoice_number = serializers.UUIDField(required=True)
    transaction_id = serializers.CharField(required=True, max_length=120)

    def validate_invoice_number(self, value):
        if CoinPackageOrder.objects.filter(invoice_number=value).exists():
            return value
        raise ValidationError(_("invoice number is invalid!"))

    def create(self, validated_data):
        raise NotImplementedError('`create()` must be implemented.')

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` must be implemented.')


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'text')
