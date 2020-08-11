from rest_framework import serializers

from ..models import Gateway


class GatewaySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Gateway
        fields = ('id', 'display_name', 'gw_type', 'code', 'image_url')

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
