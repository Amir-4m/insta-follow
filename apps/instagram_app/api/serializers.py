from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.instagram_app.models import InstaPage, UserPage, UserPackage, Package, UserInquiry, CoinTransaction
from ..services import InstagramAppService


class InstaPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = ('id', 'instagram_username')
        read_only_fields = ('id',)

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
            return page
        except Exception:
            raise ValidationError(_("the page you entered does not exists !"))


class LikedPageSerializer(serializers.Serializer):
    page_id = serializers.ListField(
        child=serializers.IntegerField()
    )


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'


class UserPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPackage
        fields = ('id', 'package')
        read_only_fields = ('id',)

    def create(self, validated_data):
        package_id = validated_data.get('package')
        user = validated_data.get('user')
        return UserPackage.objects.create(user=user, package=package_id)


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
    page_id = serializers.CharField(source='user_page.page', write_only=True)
    done_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    class Meta:
        model = UserInquiry
        fields = ('id', 'link', 'page_id', 'done_ids')

    def validate(self, attrs):
        user = self.context['request'].user
        page = attrs['user_page'].get('page')
        id_list = attrs.get('done_ids')
        try:
            user_page = UserPage.objects.get(page__instagram_username=page, user=user)
            user_inquiry = UserInquiry.objects.get(id=id_list[0], user_page=user_page)
        except UserPage.DoesNotExist:
            raise ValidationError({'Error': 'user and page does not match together !'})
        except UserInquiry.DoesNotExist:
            raise ValidationError({'Error': 'user page and inquiry does not match together !'})

        v_data = {
            'user_page': user_page,
            'user_inquiry': user_inquiry
        }
        return v_data

    def create(self, validated_data):
        user_page = validated_data.get('user_page')
        user_inquiry = validated_data.get('user_inquiry')
        InstagramAppService.check_user_action(user_inquiry, user_page)
        return True


class CoinTransactionSerializer(serializers.ModelSerializer):
    user_balance = serializers.SerializerMethodField()

    class Meta:
        model = CoinTransaction
        fields = ('id', 'user_balance', 'action')

    def get_user_balance(self, obj):
        return obj.aggregate(Sum('amount'))
