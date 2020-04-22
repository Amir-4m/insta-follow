from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.instagram_app.models import InstaPage, UserPage
from ..services import InstagramAppService


class InstaPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = ('instagram_username',)


class UserPageSerializer(serializers.ModelSerializer):
    page = InstaPageSerializer()

    class Meta:
        model = UserPage
        fields = ('page',)

    def to_representation(self, instance):
        pages = [up.page.instagram_username for up in UserPage.objects.filter(user=instance.user)]
        return {"user_pages": pages}

    def validate(self, attrs):
        page_id = attrs['page'].get('instagram_username')
        user = attrs.get('user')
        if UserPage.objects.filter(user=user, page__instagram_username=page_id).exists():
            raise ValidationError(_("You have already added this page to your account!"))
        return attrs

    def create(self, validated_data):
        page_id = validated_data['page'].get('instagram_username')
        user = validated_data.get('user')
        user_id, name, followers, following, posts_count = InstagramAppService.get_page_info(page_id)

        page, created = InstaPage.objects.get_or_create(
            instagram_username=page_id,
            defaults={
                "instagram_user_id": user_id,
                "followers": followers,
                "following": following,
                "post_no": posts_count
            }
        )
        page.save()
        return UserPage.objects.create(user=user, page=page)


class LikedPageSerializer(serializers.Serializer):
    page_id = serializers.ListField(
        child=serializers.IntegerField()
    )
