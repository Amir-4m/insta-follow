import logging
import re
import requests

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.instagram_app.tasks import check_order_validity
from apps.instagram_app.models import (
    UserInquiry, CoinTransaction, Order,
    InstaAction, Device, CoinPackage,
    CoinPackageOrder, InstaPage, Comment,
    ReportAbuse, BlockWordRegex, BlockedText,
    AllowedGateway
)

# from apps.instagram_app.services import CustomService

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
                headers={'User-Agent': user_agent},
                timeout=(3.05, 9)
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
        username = validated_data['instagram_username'].lower()
        user_id = validated_data['instagram_user_id']
        session_id = validated_data['session_id']
        page, _created = InstaPage.objects.update_or_create(
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
    description = serializers.ReadOnlyField(source='get_status_display')

    class Meta:
        model = Order
        fields = (
            'id', 'entity_id', 'action',
            'target_no', 'achieved_number_approved', 'link',
            'instagram_username', 'is_enable', 'description', 'status',
            'comments', 'shortcode', 'media_properties', 'created_time'
        )
        read_only_fields = ('is_enable', 'achieved_number_approved', 'description', 'status', 'link', 'created_time')

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
                if Comment.objects.exists():
                    attrs.update({"comments": list(Comment.objects.all().values_list('text', flat=True))})
                else:
                    raise ValidationError(detail={'detail': _('no comment is set for this order!')})
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
        instagram_username = validated_data['instagram_username'].lower()
        media_properties = validated_data.get('media_properties')

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

            ct = CoinTransaction.objects.create(
                page=page,
                amount=-(insta_action.buy_value * target_no),
                transaction_type=CoinTransaction.TYPE_ORDER
            )
            # remove order check
            order = Order.objects.create(
                entity_id=entity_id,
                action=insta_action,
                link=link,
                target_no=target_no,
                media_properties=media_properties,
                instagram_username=instagram_username,
                owner=page,
                comments=comments
            )

            ct.order = order
            ct.description = _("order %s") % insta_action.get_action_type_display()
            ct.save()

            return order


class UserInquirySerializer(serializers.ModelSerializer):
    check = serializers.BooleanField(default=False, write_only=True)
    page = serializers.ReadOnlyField(source='page.instagram_username')
    earned_coin = serializers.ReadOnlyField(source='order.action.action_value')
    done_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Order.objects.all(),
        source='order',
        required=False
    )

    class Meta:
        model = UserInquiry
        fields = ('page', 'order', 'done_id', 'status', 'earned_coin', 'check')
        extra_kwargs = {'order': {'required': False}}

    def validate_status(self, value):
        if value not in (UserInquiry.STATUS_REFUSED, UserInquiry.STATUS_VALIDATED):
            raise ValidationError(detail={'detail': _('status not correct!')})
        return value

    def validate(self, attrs):
        order = attrs.get('order', attrs.pop('done_id', None))
        if order is None:
            raise ValidationError(detail={'detail': _('done_id or order field must be filled!')})

        page = self.context['request'].auth['page']
        if UserInquiry.objects.filter(
                order__action=order.action.action_type,
                order__entity_id=order.entity_id,
                page=page
        ).exists():
            raise ValidationError(detail={'detail': _('order with this id already has been done by this page!')})
        attrs.update({'order': order, 'page_id': page.id})
        return attrs

    def create(self, validated_data):
        page = self.context['request'].auth['page']
        order = validated_data['order']
        check = validated_data.pop('check')

        try:
            user_inquiry = super().create(validated_data)
        except Exception as e:
            logger.error(f'error in creating inquiry for page {page.id} with order {order.id}: {e}')
            raise ValidationError(detail={'detail': _(f'error occurred while creating inquiry. try again later.')})

        if check is True:
            check_order_validity.delay(order.pk)

        if user_inquiry.status == UserInquiry.STATUS_VALIDATED and order.owner != page and order.instagram_username != page.instagram_username:
            CoinTransaction.objects.create(
                page=user_inquiry.page,
                inquiry=user_inquiry,
                amount=user_inquiry.order.action.action_value,
                transaction_type=CoinTransaction.TYPE_INQUIRY
            )

            if user_inquiry.order.action.action_type in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]:
                user_inquiry.validated_time = timezone.now()
                user_inquiry.save()

        # _ck = f"order_{order.id}_assigned"
        # try:
        #     cache.decr(_ck)
        # except Exception:
        #     logger.warning(f'cache with key {_ck} does not exists!')

        return user_inquiry


class CoinTransactionSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()

    class Meta:
        model = CoinTransaction
        exclude = ('page',)

    def get_description(self, obj):
        if obj.transaction_type == obj.TYPE_ORDER:
            return _("order %s") % obj.order.action.get_action_type_display()
        elif obj.transaction_type == obj.TYPE_INQUIRY:
            return _("done %s") % obj.inquiry.order.action.get_action_type_display()
        return obj.get_transaction_type_display()


class InstaActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaAction
        fields = ('action_type', 'action_value', 'buy_value')


class CoinPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPackage
        fields = (
            'id', 'name', 'sku', 'amount',
            'price', 'is_enable', 'is_featured',
            'featured', 'price_offer', 'amount_offer'
        )


class CoinPackageOrderSerializer(serializers.ModelSerializer):
    gateways = serializers.SerializerMethodField(read_only=True)
    package_detail = serializers.SerializerMethodField()

    class Meta:
        model = CoinPackageOrder
        fields = (
            'id', 'invoice_number', 'coin_package',
            'page', 'is_paid', 'price', 'package_detail',
            'version_name', 'gateways', 'created_time', 'redirect_url'
        )
        read_only_fields = ('page',)

    def get_package_detail(self, obj):
        if obj.coin_package:
            return CoinPackageSerializer(obj.coin_package).data

    def get_gateways(self, obj):
        gateways_list = []
        if self.context['view'].action != 'create':
            return gateways_list

        try:
            gateways_list = list(AllowedGateway.get_gateways_by_version_name(obj.version_name))
        except Exception as e:
            logger.error(f"getting gateways list failed in creating package order: {e}")
        return gateways_list


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

    def validate(self, attrs):
        amount = attrs['amount']
        username = attrs['to_page']
        page = self.context['request'].auth['page']
        transfers_done = page.coin_transactions.filter(
            to_page__isnull=False,
            created_time__gte=timezone.now().replace(hour=0, minute=0, second=0)
        ).count()
        if transfers_done >= settings.DAILY_TRANSFER_LIMIT:
            raise ValidationError(detail={'detail': _("you've reached today's transfer limit!")})
        if amount > settings.MAXIMUM_COIN_TRANSFER or amount <= 0:
            raise ValidationError(detail={'detail': _("Transfer amount is invalid!")})
        if not InstaPage.objects.filter(instagram_username__iexact=username).exists():
            raise ValidationError(detail={'detail': _('Target page does not exists')})
        return attrs

    def create(self, validated_data):
        sender = validated_data.get('sender')
        real_amount = validated_data['amount']
        target = validated_data['to_page'].lower()
        fee_amount = real_amount + settings.COIN_TRANSFER_FEE
        if sender.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0))['wallet'] < fee_amount:
            raise ValidationError(detail={'detail': _("Transfer amount is higher than your coin balance!")})
        if real_amount > settings.MAXIMUM_COIN_TRANSFER:
            raise ValidationError(detail={'detail': _("Transfer amount is invalid!")})
        with transaction.atomic():
            qs = InstaPage.objects.select_for_update()
            sender_page = qs.get(id=sender.id)
            target_page = qs.get(instagram_username=target)
            sender_transaction = CoinTransaction.objects.create(
                page=sender_page,
                amount=-fee_amount,
                to_page=target_page,
                transaction_type=CoinTransaction.TYPE_TRANSFER
            )
            CoinTransaction.objects.create(
                page=target_page,
                amount=real_amount,
                from_page=sender_page,
                transaction_type=CoinTransaction.TYPE_TRANSFER

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
