import requests
from rest_framework import serializers
from instagram_app.models import InstaPage, UserPage


class InstaPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaPage
        fields = ('instagram_username',)


class UserPageSerializer(InstaPageSerializer):
    page = InstaPageSerializer()

    class Meta:
        model = UserPage
        fields = ('page',)

    def create(self, validated_data):
        username = validated_data['page'].get('instagram_username')
        user = validated_data.get('user')
        response = requests.get(f"https://www.instagram.com/{username}/?__a=1").json()
        temp = response['graphql']['user']
        user_id = temp['id']
        name = temp['full_name']
        followers = temp['edge_followed_by']['count']
        following = temp['edge_follow']['count']
        posts_count = temp['edge_owner_to_timeline_media']['count']
        page = InstaPage.objects.create(
            instagram_username=username,
            instagram_user_id=user_id,
            followers=followers,
            following=following,
            post_no=posts_count,
        )
        user_page = UserPage.objects.create(
            user=user,
            page=page
        )
        return user_page

    def validate(self, attrs):
        print(attrs)
        return super(UserPageSerializer, self).validate(attrs)


class LikedPageSerializer(serializers.Serializer):
    page_id = serializers.ListField(
        child=serializers.IntegerField()
    )
