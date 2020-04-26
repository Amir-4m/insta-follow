from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.instagram_app.models import InstaPage, UserPage, UserPackage, Package
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
