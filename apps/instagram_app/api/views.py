from itertools import accumulate

from rest_framework import status, mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (
    InstaPageSerializer,
    LikedPageSerializer,
    UserPackageSerializer,
    PackageSerializer,
    OrderSerializer,
    UserInquirySerializer
)
from apps.instagram_app.models import (
    InstaPage, UserPage, Order,
    UserPackage, Package, UserInquiry,
    Action
)


class InstaPageViewSet(mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
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


class PackageViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = PackageSerializer
    queryset = Package.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_enable=True)


class UserPackageViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = UserPackageSerializer
    queryset = UserPackage.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserInquiryViewSet(viewsets.GenericViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = UserInquiry.objects.all()
    serializer_class = UserInquirySerializer

    def get_inquiry(self, request, action_type):
        page_id = request.data.get('page_id')
        if not page_id:
            return Response({'Error': 'page_id is required'})
        user_page = UserPage.objects.get(page_id=page_id)
        valid_orders = Order.objects.filter(is_enable=True, action_type=action_type).order_by('-id')

        valid_inquiries = []
        for order in valid_orders:
            user_inquiry, _c = UserInquiry.objects.get_or_create(order=order, defaults=dict(user_page=user_page))
            if _c or user_inquiry.validated_time is None:
                valid_inquiries.append(user_inquiry)
            # TODO: condition will change duo to package
            if len(valid_inquiries) == 5:
                break

        serializer = self.serializer_class(valid_inquiries, many=True)
        return Response(serializer.data)

    @action(methods=["post"], detail=False, url_path="like")
    def like(self, request, *args, **kwargs):
        return self.get_inquiry(request, Action.LIKE)

    @action(methods=['post'], detail=False, url_path="comment")
    def comment(self, request, *args, **kwargs):
        return self.get_inquiry(request, Action.COMMENT)

    @action(methods=['post'], detail=False, url_path="follow")
    def follow(self, request, *args, **kwargs):
        return self.get_inquiry(request, Action.FOLLOW)
