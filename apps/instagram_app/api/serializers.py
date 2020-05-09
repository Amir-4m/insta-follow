from django.db import transaction
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.instagram_app.models import InstaPage, UserPage, UserInquiry, CoinTransaction, Order, InstaAction
from apps.instagram_app.services import InstagramAppService
from apps.accounts.models import User


class InstaPagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = ('id', 'instagram_username', 'instagram_user_id')


class ProfileSerializer(serializers.ModelSerializer):
    insta_pages = serializers.SerializerMethodField(read_only=True)
    approved_wallet = serializers.SerializerMethodField(read_only=True)
    unapproved_wallet = serializers.SerializerMethodField(read_only=True)
    instagram_username = serializers.CharField(write_only=True)
    user_id = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'insta_pages', 'approved_wallet', 'unapproved_wallet', 'instagram_username', 'user_id')
        read_only_fields = ('id',)

    def get_approved_wallet(self, obj):
        # TODO: arash fix
        return obj.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet') or 0

    def get_unapproved_wallet(self, obj):
        # TODO: arash fix
        return UserInquiry.objects.filter(
            user_page__user=obj,
            status=UserInquiry.STATUS_DONE,
            done_time__isnull=False
        ).aggregate(coins=Sum('order__action__action_value')).get('coins') or 0

    def get_insta_pages(self, obj):
        qs = obj.insta_pages.filter(user_pages__is_active=True)
        return InstaPagesSerializer(qs, many=True).data

    def create(self, validated_data):
        page_id = validated_data.get('instagram_username')
        user_id = validated_data.get('user_id')
        user = self.context['request'].user
        page, created = InstaPage.objects.get_or_create(
            instagram_user_id=user_id,
            instagram_username=page_id,
        )
        UserPage.objects.get_or_create(user=user, page=page)
        return user


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'action', 'target_no', 'link', 'instagram_username', 'is_enable')
        extra_kwargs = {
            'link': {'required': False}
        }

    def validate(self, attrs):
        action_value = attrs.get('action')
        link = attrs.get('link')
        instagram_username = attrs.get('instagram_username')
        if (action_value.pk == InstaAction.ACTION_LIKE or action_value.pk == InstaAction.ACTION_COMMENT) and not link:
            raise ValidationError({'link': 'this field is required for like and comment !'})
        elif action_value.pk == InstaAction.ACTION_FOLLOW and not instagram_username:
            raise ValidationError({'instagram_username': 'this field is required for follow !'})
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
            if user.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0)).get('wallet', 0) < insta_action.buy_value * target_no:
                raise ValidationError(_("You do not have enough coin to create order"))

            ct = CoinTransaction.objects.create(user=user, amount=-(insta_action.buy_value * target_no))
            order = Order.objects.create(
                action=insta_action,
                link=link,
                target_no=target_no,
                owner=user,
            )
            ct.order = order
            ct.save()
            return order


class UserInquirySerializer(serializers.ModelSerializer):
    link = serializers.ReadOnlyField(source="order.link")
    media_url = serializers.ReadOnlyField(source="order.media_url")
    page_id = serializers.IntegerField(write_only=True)
    done_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    instagram_username = serializers.ReadOnlyField(source='order.instagram_username')

    class Meta:
        model = UserInquiry
        fields = ('id', 'link', 'instagram_username', 'media_url', 'page_id', 'done_ids')

    def validate(self, attrs):
        user = self.context['request'].user
        page_id = attrs.get('page_id')
        id_list = attrs.get('done_ids')
        try:
            user_page = UserPage.objects.get(page=page_id, user=user)
            user_inquiry_ids = [obj.id for obj in UserInquiry.objects.filter(id__in=id_list, user_page=user_page)]
        except UserPage.DoesNotExist:
            raise ValidationError({'Error': 'user and page does not match together !'})
        except Exception as e:
            raise ValidationError({'Error': f"{e}"})
        if len(user_inquiry_ids) != len(id_list):
            raise ValidationError({'Error': 'invalid id for user inquiries'})

        v_data = {
            'user_page': user_page,
            'user_inquiry_ids': user_inquiry_ids
        }
        return v_data

    def create(self, validated_data):
        user_page = validated_data.get('user_page')
        user_inquiry_ids = validated_data.get('user_inquiry_ids')
        InstagramAppService.check_user_action(user_inquiry_ids, user_page.id)
        return True


class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinTransaction
        exclude = ('user',)


class InstaActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaAction
        fields = ('action_type', 'action_value', 'buy_value')
