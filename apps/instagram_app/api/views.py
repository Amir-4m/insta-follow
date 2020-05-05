from rest_framework import status, mixins, viewsets, views, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from .serializers import (
    ProfileSerializer,
    OrderSerializer,
    UserInquirySerializer,
    CoinTransactionSerializer
)
from ..pagination import CoinTransactionPagination
from apps.accounts.models import User
from apps.instagram_app.models import (
    InstaAction, UserPage, Order,
    UserInquiry, CoinTransaction
)


class ProfileViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = ProfileSerializer
    queryset = User.objects.all()
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return queryset.filter(id=user.id)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        serializer = ProfileSerializer(self.get_queryset(), many=True)
        response.data = serializer.data
        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        page_id = kwargs.get('pk')
        UserPage.objects.filter(page=page_id, user=self.request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# class PackageViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
#     authentication_classes = (JWTAuthentication,)
#     permission_classes = (IsAuthenticated,)
#     serializer_class = PackageSerializer
#     queryset = Package.objects.all()
#
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         return queryset.filter(is_enable=True)
#
#
# class UserPackageViewSet(mixins.CreateModelMixin,
#                          mixins.RetrieveModelMixin,
#                          mixins.ListModelMixin,
#                          viewsets.GenericViewSet):
#     authentication_classes = (JWTAuthentication,)
#     permission_classes = (IsAuthenticated,)
#     serializer_class = UserPackageSerializer
#     queryset = UserPackage.objects.all()
#
#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)


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
        valid_orders = Order.objects.filter(is_enable=True, action=action_type).order_by('-id')

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
        return self.get_inquiry(request, InstaAction.ACTION_LIKE)

    @action(methods=['get'], detail=False, url_path="comment")
    def comment(self, request, *args, **kwargs):
        return self.get_inquiry(request, InstaAction.ACTION_COMMENT)

    @action(methods=['get'], detail=False, url_path="follow")
    def follow(self, request, *args, **kwargs):
        return self.get_inquiry(request, InstaAction.ACTION_FOLLOW)

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
