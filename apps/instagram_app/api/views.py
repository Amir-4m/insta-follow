from django.utils.translation import ugettext_lazy as _
from django.db.models import Sum
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets, generics, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response

from ..swagger_schemas import ORDER_POST_DOCS, INQUIRY_POST_DOC, PROFILE_POST_DOC
from .serializers import (
    ProfileSerializer,
    OrderSerializer,
    UserInquirySerializer,
    CoinTransactionSerializer,
    InstaActionSerializer,
    DeviceSerializer
)
from ..pagination import CoinTransactionPagination, OrderPagination
from ..tasks import collect_order_link_info
from apps.instagram_app.models import (
    InstaAction, UserPage, Order,
    UserInquiry, CoinTransaction, Device
)


class DeviceViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = DeviceSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = Device.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="Get a list of user instagram pages and his/her coin balance",
    responses={"200": 'Successful'}
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=PROFILE_POST_DOC

))
class ProfileViewSet(viewsets.ViewSet):
    serializer_class = ProfileSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer = ProfileSerializer(data=self.request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def list(self, request):
        serializer = self.serializer_class(self.request.user)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        UserPage.objects.filter(page=pk, user=self.request.user).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="Get a list of user submitted orders",
    responses={"200": 'Successful'}
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="Create an order with a chosen action for the post or profile that user requested",
    request_body=ORDER_POST_DOCS
))
class OrderViewSet(viewsets.GenericViewSet,
                   mixins.CreateModelMixin,
                   mixins.ListModelMixin):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    pagination_class = OrderPagination

    def get_queryset(self):
        qs = super(OrderViewSet, self).get_queryset()
        return qs.filter(owner=self.request.user).order_by('-created_time')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(methods=["get"], detail=True)
    def recheck(self, request, pk=None, *args, **kwargs):
        """
        Check whether or not the account is private or not
        """
        instance = self.get_object()
        if instance.is_enable is False:
            collect_order_link_info.delay(
                order_id=instance.id,
                action=instance.action.action_type,
                link=instance.link,
                media_url=instance.media_url,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserInquiryViewSet(viewsets.ViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = UserInquiry.objects.all()
    serializer_class = UserInquirySerializer

    def get_inquiry(self, request, action_type):
        page_id = request.query_params.get('page_id')
        if not page_id:
            return Response({'Error': _('page_id is required')}, status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = abs(min(int(request.query_params.get('limit', 0)), 100))
        except ValueError:
            raise ValidationError(detail={'detail': _('make sure the limit value is a positive number!')})

        try:
            user_page = UserPage.objects.get(page_id=page_id, user=self.request.user)
        except UserPage.DoesNotExist:
            raise ValidationError(detail={'detail': _('user and page does not match!')})
        valid_orders = Order.objects.filter(is_enable=True, action=action_type).order_by('-id')

        valid_inquiries = []
        given_entities = []
        for order in valid_orders:
            if order.entity_id in given_entities:
                continue
            user_inquiry, _c = UserInquiry.objects.get_or_create(order=order, defaults=dict(user_page=user_page))
            if user_inquiry:
                valid_inquiries.append(user_inquiry)
                given_entities.append(order.entity_id)
            if len(valid_inquiries) == limit:
                break

        serializer = self.serializer_class(valid_inquiries, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="like")
    def like(self, request, *args, **kwargs):
        """Get a list of like orders that user must like them"""
        return self.get_inquiry(request, InstaAction.ACTION_LIKE)

    @action(methods=['get'], detail=False, url_path="comment")
    def comment(self, request, *args, **kwargs):
        """Get a list of comment orders that user must comment for them"""
        return self.get_inquiry(request, InstaAction.ACTION_COMMENT)

    @action(methods=['get'], detail=False, url_path="follow")
    def follow(self, request, *args, **kwargs):
        """Get a list of follow orders that user must follow"""
        return self.get_inquiry(request, InstaAction.ACTION_FOLLOW)

    @swagger_auto_schema(
        operation_description='Check whether or not the user did the action properly for the order such as (like, comment or follow).',
        method='post',
        request_body=INQUIRY_POST_DOC

    )
    @action(methods=['post'], detail=False, url_path="done")
    def post(self, request, *args, **kwargs):
        serializer = UserInquirySerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()


class CoinTransactionAPIView(viewsets.GenericViewSet, mixins.ListModelMixin):
    """Shows a list of user transactions"""
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = CoinTransaction.objects.all()
    serializer_class = CoinTransactionSerializer
    pagination_class = CoinTransactionPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user).order_by('-created_time')

    @action(methods=['get'], detail=False, url_path='total')
    def total(self, request, *args, **kwargs):
        serializer = self.serializer_class(self.get_queryset().aggregate(amount=Sum('amount')))
        return Response(serializer.data)


class InstaActionAPIView(generics.ListAPIView):
    """Get a list of action types and their values"""
    queryset = InstaAction.objects.all()
    serializer_class = InstaActionSerializer
