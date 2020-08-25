from rest_framework import views
from rest_framework.response import Response

from apps.instagram_app.authentications import PageAuthentication

from ..models import Config


class ConfigAPIView(views.APIView):
    """Shows init configs params"""
    authentication_classes = (PageAuthentication,)

    def get(self, request, *args, **kwargs):
        configs = Config.objects.all()
        data = {}
        if configs:
            for config in configs:
                data.update({config.name: config.value})
        return Response(data)
