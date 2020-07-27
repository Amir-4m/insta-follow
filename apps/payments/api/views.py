from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import GatewaySerializer
from ..models import Gateway


class GatewayViewSet(viewsets.GenericViewSet, generics.ListAPIView):
    queryset = Gateway.objects.all()
    serializer_class = GatewaySerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
