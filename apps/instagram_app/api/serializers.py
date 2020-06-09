from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, ParseError

from apps.instagram_app.models import InstaPage, UserPage, UserInquiry, CoinTransaction, Order, InstaAction, Device
from apps.accounts.models import User


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('device_id',)

    def create(self, validated_data):
        user = validated_data.get('user')
        device_id = validated_data.get('device_id')
        return Device.objects.create(user=user, device_id=device_id)


class InstaPagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = ('id', 'instagram_username', 'instagram_user_id')


class ProfileSerializer(serializers.ModelSerializer):
    insta_pages = serializers.SerializerMethodField(read_only=True)
    approved_wallet = serializers.SerializerMethodField(read_only=True)
    unapproved_wallet = serializers.SerializerMethodField(read_only=True)
    instagram_username = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'insta_pages', 'approved_wallet', 'unapproved_wallet', 'instagram_username')
        read_only_fields = ('id',)

    def get_approved_wallet(self, obj):
        return obj.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0))['wallet']

    def get_unapproved_wallet(self, obj):
        return UserInquiry.objects.filter(
            user_page__user=obj,
            status=UserInquiry.STATUS_DONE,
        ).aggregate(coins=Coalesce(Sum('order__action__action_value'), 0))['coins']

    def get_insta_pages(self, obj):
        qs = obj.insta_pages.filter(user_pages__is_active=True)
        return InstaPagesSerializer(qs, many=True).data

    def create(self, validated_data):
        page_id = validated_data.get('instagram_username')
        user = self.context['user']
        page, created = InstaPage.objects.get_or_create(
            instagram_username=page_id,
        )
        UserPage.objects.update_or_create(
            user=user,
            page=page,
            defaults={
                'is_active': True
            }
        )
        return user


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'id', 'entity_id', 'action',
            'target_no', 'achieved_number_approved', 'link',
            'instagram_username', 'is_enable', 'description',
            'media_url'
        )
        read_only_fields = ('entity_id', 'is_enable', 'achieved_number_approved', 'description')
        extra_kwargs = {
            'link': {'allow_null': True, 'required': False, 'allow_blank': True}
        }

    def validate(self, attrs):
        action_value = attrs.get('action')
        link = attrs.get('link')
        instagram_username = attrs.get('instagram_username')
        if (action_value.pk == InstaAction.ACTION_LIKE or action_value.pk == InstaAction.ACTION_COMMENT) and not link:
            raise ValidationError(detail={'detail': _('link field is required for like and comment !')})
        if action_value.pk == InstaAction.ACTION_FOLLOW and not instagram_username:
            raise ValidationError(
                detail={'detail': _('instagram_username field is required for follow!')})
        return attrs

    def create(self, validated_data):
        user = validated_data.get('user')
        insta_action = validated_data.get('action')
        target_no = validated_data.get('target_no')
        link = validated_data.get('link')
        if insta_action.pk == InstaAction.ACTION_FOLLOW:
            instagram_username = validated_data.get('instagram_username')
            link = f"https://www.instagram.com/{instagram_username}/"

        with transaction.atomic():
            user = User.objects.select_for_update().get(id=user.id)
            if user.coin_transactions.all().aggregate(
                    wallet=Coalesce(Sum('amount'), 0)
            )['wallet'] < insta_action.buy_value * target_no:
                raise ValidationError(detail={'detail': _("You do not have enough coin to create order")})

            ct = CoinTransaction.objects.create(user=user, amount=-(insta_action.buy_value * target_no))
            order = Order.objects.create(
                action=insta_action,
                link=link,
                target_no=target_no,
                owner=user,
            )
            ct.order = order
            ct.description = f"create order {order.id}"
            ct.save()
            return order


class UserInquirySerializer(serializers.ModelSerializer):
    link = serializers.ReadOnlyField(source="order.link")
    media_url = serializers.ReadOnlyField(source="order.media_url")
    instagram_username = serializers.ReadOnlyField(source='order.instagram_username')
    user_page = serializers.ReadOnlyField(source='user_page.page.instagram_username')
    action = serializers.ReadOnlyField(source='order.action.action_type')
    done_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    class Meta:
        model = UserInquiry
        fields = ('id', 'link', 'instagram_username', 'media_url', 'done_ids', 'status', 'user_page', 'action')

    def validate_done_ids(self, value):
        user = self.context['request'].user
        id_list = UserInquiry.objects.filter(
            id__in=value, user_page__user=user, status=UserInquiry.STATUS_OPEN
        ).values_list('id', flat=True)
        if not id_list:
            raise ParseError(_('list is not valid!'))


class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinTransaction
        exclude = ('user',)


class InstaActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaAction
        fields = ('action_type', 'action_value', 'buy_value')
