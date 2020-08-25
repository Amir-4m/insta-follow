import logging
import random
import re

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, ParseError

from apps.instagram_app.models import (
    UserInquiry, CoinTransaction, Order,
    InstaAction, Device, CoinPackage,
    CoinPackageOrder, InstaPage, Comment,
    ReportAbuse, BlockWordRegex, BlockedText
)
from apps.instagram_app.services import CustomService

logger = logging.getLogger(__name__)


class LoginVerificationSerializer(serializers.ModelSerializer):
    instagram_user_id = serializers.IntegerField()

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
        except Exception as e:
            logger.error(f"error in login verification for user id {user_id}: {e}")
            raise ValidationError(
                detail={'detail': _('error occurred while logging in!')}
            )

        if (temp['pk'] != user_id or temp['username'] != username) or temp.get('account_type') is None:
            raise ValidationError(
                detail={'detail': _('invalid credentials provided!')}
            )

        return attrs

    def create(self, validated_data):
        username = validated_data['instagram_username']
        user_id = validated_data['instagram_user_id']
        session_id = validated_data['session_id']
        page, _created = InstaPage.objects.get_or_create(
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


class OrderSerializer(serializers.ModelSerializer):
    shortcode = serializers.CharField(required=False)

    class Meta:
        model = Order
        fields = (
            'id', 'entity_id', 'action',
            'target_no', 'achieved_number_approved', 'link',
            'instagram_username', 'is_enable', 'description',
            'media_url', 'comments', 'shortcode'
        )
        read_only_fields = ('is_enable', 'achieved_number_approved', 'description', 'link')

    def validate(self, attrs):
        action_value = attrs.get('action')
        shortcode = attrs.get('shortcode')
        instagram_username = attrs.get('instagram_username')
        comments = attrs.get('comments')

        if action_value.pk in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT] and not shortcode:
            raise ValidationError(detail={'detail': _('shortcode field is required for like and comment !')})

        if action_value.pk == InstaAction.ACTION_FOLLOW and not instagram_username:
            raise ValidationError(
                detail={'detail': _('instagram_username field is required for follow!')}
            )

        if action_value.pk in [InstaAction.ACTION_LIKE, InstaAction.ACTION_FOLLOW] and comments is not None:
            attrs.update({"comments": None})

        elif action_value.pk == InstaAction.ACTION_COMMENT:
            if not comments:
                attrs.update({"comments": list(Comment.objects.all().values_list('text', flat=True))})
            else:
                regex = BlockWordRegex.objects.all()
                for reg in regex:
                    r = re.compile(reg.pattern)
                    results = list(filter(r.match, comments))
                    if results:
                        BlockedText.objects.create(
                            text=results[0],
                            pattern=reg,
                            author=self.context['request'].auth['page']
                        )
                        raise ValidationError(detail={'detail': _('inappropriate word has been found in the text!')})
        return attrs

    def create(self, validated_data):
        entity_id = validated_data.get('entity_id')
        page = validated_data.get('page')
        insta_action = validated_data.get('action')
        target_no = validated_data.get('target_no')
        comments = validated_data.get('comments')
        instagram_username = validated_data.get('instagram_username')

        if insta_action.pk == InstaAction.ACTION_FOLLOW:
            link = f"https://www.instagram.com/{instagram_username}/"
        else:
            shortcode = validated_data.get('shortcode')
            link = f"https://www.instagram.com/p/{shortcode}/"

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
                instagram_username=instagram_username,
                owner=page,
                comments=comments
            )
            ct.order = order
            ct.description = f"create order {order.id}"
            ct.save()

            return order


class UserInquirySerializer(serializers.ModelSerializer):
    link = serializers.ReadOnlyField(source="order.link")
    instagram_username = serializers.ReadOnlyField(source='order.instagram_username')
    page = serializers.ReadOnlyField(source='page.instagram_username')
    action = serializers.ReadOnlyField(source='order.action.action_type')
    comment = serializers.SerializerMethodField()
    done_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    class Meta:
        model = UserInquiry
        fields = ('id', 'instagram_username', 'link', 'done_ids', 'status', 'page', 'action', 'comment')

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
        fields = ('name', 'sku', 'package_amount', 'package_price', 'is_enable', 'featured')


class CoinPackageOrderSerializer(serializers.ModelSerializer):
    gateways = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoinPackageOrder
        fields = ('id', 'invoice_number', 'coin_package', 'page', 'is_paid', 'price', 'gateways')
        read_only_fields = ('page',)

    def get_gateways(self, obj):
        try:
            response = CustomService.payment_request('gateways', 'get')
            data = response.json()
        except Exception as e:
            logger.error(f"error calling payment with endpoint gateways/ and action get: {e}")
            data = {}
        return data


class PurchaseSerializer(serializers.Serializer):
    purchase_token = serializers.CharField(max_length=50, allow_null=True)
    gateway_code = serializers.CharField(max_length=10)
    package_order = serializers.PrimaryKeyRelatedField(queryset=CoinPackageOrder.objects.filter(is_paid=None))

    def validate(self, attrs):
        gateway_code = attrs['gateway_code']
        purchase_token = attrs.get('purchase_token')
        if gateway_code == 'BAZAAR' and purchase_token is None:
            raise ValidationError(detail={'detail': _('purchase_token is required for gateway bazaar!')})
        return attrs

    def create(self, validated_data):
        raise NotImplementedError('`create()` must be implemented.')

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` must be implemented.')


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'text')


class CoinTransferSerializer(serializers.ModelSerializer):
    to_page = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = CoinTransaction
        fields = ('amount', 'to_page')

    def validate_amount(self, value):
        if value > settings.MAXIMUM_COIN_TRANSFER or value <= 0:
            raise ValidationError(detail={'detail': _("Transfer amount is invalid!")})
        return value

    def validate_to_page(self, value):
        if InstaPage.objects.filter(instagram_username=value).exists():
            return value
        raise ValidationError(detail={'detail': _('Target page does not exists')})

    def create(self, validated_data):
        sender = validated_data.get('sender')
        amount = validated_data['amount']
        target = validated_data['to_page']
        if sender.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0))['wallet'] < amount:
            raise ValidationError(detail={'detail': _("Transfer amount is higher than your coin balance!")})
        with transaction.atomic():
            qs = InstaPage.objects.select_for_update()
            sender_page = qs.get(id=sender.id)
            target_page = qs.get(instagram_username=target)
            sender_transaction = CoinTransaction.objects.create(
                page=sender_page,
                amount=-amount,
                description=_("transfer to page %s") % target_page,
                to_page=target_page
            )
            CoinTransaction.objects.create(
                page=target_page,
                amount=amount,
                description=_("transfer from page %s") % sender_page,
                from_page=sender_page
            )
            return sender_transaction


class ReportAbuseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAbuse
        fields = ('text', 'abuser')

    def validate_abuser(self, value):
        if Order.objects.filter(id=value.id).exists():
            return value
        raise ValidationError(detail={'detail': _("order does not exists!")})

    def create(self, validated_data):
        text = validated_data['text']
        reporter = validated_data.get('reporter')
        abuser = validated_data['abuser']
        report = ReportAbuse.objects.create(text=text, reporter=reporter, abuser=abuser)
        return report


class PackageOrderGateWaySerializer(serializers.Serializer):
    gateway = serializers.IntegerField()
    package_order = serializers.PrimaryKeyRelatedField(queryset=CoinPackageOrder.objects.filter(is_paid=None))

    def create(self, validated_data):
        raise NotImplementedError('`create()` must be implemented.')

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` must be implemented.')
