from rest_framework import status, mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import InstaPageSerializer, LikedPageSerializer
from apps.instagram_app.models import InstaPage, UserPage


class InstaPageViewSet(mixins.CreateModelMixin,
                       mixins.DestroyModelMixin,
                       mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    serializer_class = InstaPageSerializer
    queryset = InstaPage.objects.all()
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return queryset.filter(owner=user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        serializer = InstaPageSerializer(InstaPage.objects.filter(owner=self.request.user), many=True)
        response.data = serializer.data
        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        UserPage.objects.filter(page=instance, user=self.request.user).delete()


class LikedPageAPIVIEW(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = LikedPageSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
