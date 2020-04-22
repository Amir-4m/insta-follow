from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import UserPageSerializer, LikedPageSerializer
from apps.instagram_app.models import UserPage


class UserPageViewSet(viewsets.ModelViewSet):
    serializer_class = UserPageSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return UserPage.objects.filter(user=user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


class LikedPageAPIVIEW(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = LikedPageSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
