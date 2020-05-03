from itertools import accumulate
from rest_framework import status, mixins, viewsets, views, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from .serializers import (
    InstaPageSerializer,
    LikedPageSerializer,
    UserPackageSerializer,
    PackageSerializer,
    OrderSerializer,
    UserInquirySerializer,
    CoinTransactionSerializer
)
from ..pagination import CoinTransactionPagination
from apps.instagram_app.models import (
    InstaPage, UserPage, Order,
    UserPackage, Package, UserInquiry, CoinTransaction
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


class LikedPageAPIVIEW(views.APIView):
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


class UserInquiryViewSet(viewsets.ViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = UserInquiry.objects.all()
    serializer_class = UserInquirySerializer

    def get_inquiry(self, request, action_type):
        page_id = request.query_params.get('page_id')
        if not page_id:
            return Response({'Error': 'page_id is required'})

        try:
            limit = abs(min(int(request.query_params.get('limit', 0)), 100))
        except TypeError:
            raise ValidationError('make sure the limit value is a positive number!')

        try:
            user_page = UserPage.objects.get(page_id=page_id, user=self.request.user)
        except UserPage.DoesNotExist:
            raise ValidationError({'Error': 'user and page does not match!'})
        valid_orders = Order.objects.filter(is_enable=True, action_type=action_type).order_by('-id')

        valid_inquiries = []
        for order in valid_orders:
            user_inquiry, _c = UserInquiry.objects.get_or_create(order=order, defaults=dict(user_page=user_page))
            # if _c or user_inquiry.validated_time is None:
            if _c:
                valid_inquiries.append(user_inquiry)
            if len(valid_inquiries) == limit:
                break

        serializer = self.serializer_class(valid_inquiries, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="like")
    def like(self, request, *args, **kwargs):
        return self.get_inquiry(request, 'L')

    @action(methods=['get'], detail=False, url_path="comment")
    def comment(self, request, *args, **kwargs):
        return self.get_inquiry(request, 'C')

    @action(methods=['get'], detail=False, url_path="follow")
    def follow(self, request, *args, **kwargs):
        return self.get_inquiry(request, 'F')

    @action(methods=['post'], detail=False, url_path="done")
    def post(self, request, *args, **kwargs):
        serializer = UserInquirySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()


class CoinTransactionAPIView(generics.ListAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = CoinTransaction.objects.all()
    serializer_class = CoinTransactionSerializer
    pagination_class = CoinTransactionPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user).order_by('-created_time')
