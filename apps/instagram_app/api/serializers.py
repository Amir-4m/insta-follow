from abc import ABC
from django.db.models import Sum, F
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.instagram_app.models import InstaPage, UserPage, UserInquiry, CoinTransaction
from apps.instagram_app.tasks import check_user_action
from apps.instagram_app.services import InstagramAppService
from apps.accounts.models import User


class InstaPagesObjectRelatedField(serializers.RelatedField, ABC):
    """
        A custom field to use for the `insta_page_object` generic relationship.
        """

    def to_representation(self, value):
        """
        Serialize insta page objects to a simple textual representation.
        """
        if isinstance(value, InstaPage):
            return {'id': value.id, 'instagram_username': value.instagram_username}
        raise Exception('Unexpected type of insta page object')


class ProfileSerializer(serializers.ModelSerializer):
    insta_pages = InstaPagesObjectRelatedField(read_only=True, many=True)
    wallet = serializers.SerializerMethodField(read_only=True)
    instagram_username = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'insta_pages', 'wallet', 'instagram_username')
        read_only_fields = ('id',)

    def get_wallet(self, obj):
        return obj.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet')

    def create(self, validated_data):
        page_id = validated_data.get('instagram_username')
        user = validated_data.get('user')
        try:
            user_id, name, followers, following, posts_count = InstagramAppService.get_page_info(page_id)
            page, created = InstaPage.objects.update_or_create(
                instagram_user_id=user_id,
                defaults={
                    "instagram_username": page_id,
                    "followers": followers,
                    "following": following,
                    "post_no": posts_count
                }
            )
            UserPage.objects.get_or_create(user=user, page=page)
            return user
        except Exception:
            raise ValidationError(_("the page you entered does not exists !"))


# class PackageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Package
#         fields = '__all__'
#
#
# class UserPackageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserPackage
#         fields = ('id', 'package')
#         read_only_fields = ('id',)
#
#     def create(self, validated_data):
#         package_id = validated_data.get('package')
#         user = validated_data.get('user')
#         return UserPackage.objects.create(user=user, package=package_id)


class OrderSerializer(serializers.Serializer):
    follow = serializers.IntegerField(allow_null=True, required=False)
    like = serializers.IntegerField(allow_null=True, required=False)
    comment = serializers.IntegerField(allow_null=True, required=False)
    link = serializers.URLField(allow_null=False, allow_blank=False)
    page_id = serializers.CharField(max_length=100, allow_blank=False, allow_null=True)

    def to_representation(self, data):
        lst = []
        if not isinstance(data, list):
            return model_to_dict(data)
        else:
            for ins in data:
                lst.append(model_to_dict(ins))
            return {'created_orders': lst}

    def create(self, validated_data):
        return InstagramAppService.create_order(**validated_data)

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` must be implemented.')


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
        check_user_action.delay(user_inquiry_ids, user_page.id)
        return True


class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinTransaction
        exclude = ('user',)
