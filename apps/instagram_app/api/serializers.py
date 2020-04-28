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

    class Meta:
        model = UserInquiry
        fields = ('id', 'link')


class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinTransaction
        fields = '__all__'

    def to_representation(self, queryset):
        return {'user_balance': sum([instance.amount for instance in queryset])}
