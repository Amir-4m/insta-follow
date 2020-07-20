import requests
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, generics, mixins, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend

from ..swagger_schemas import ORDER_POST_DOCS, INQUIRY_POST_DOC, PROFILE_POST_DOC
from .serializers import (
    ProfileSerializer,
    OrderSerializer,
    UserInquirySerializer,
    CoinTransactionSerializer,
    InstaActionSerializer,
    DeviceSerializer,
    CoinPackageSerializer)
from ..services import CustomService
from ..pagination import CoinTransactionPagination, OrderPagination, InquiryPagination
from ..tasks import collect_order_link_info
from apps.instagram_app.models import (
    InstaAction, UserPage, Order,
    UserInquiry, CoinTransaction, Device,
    CoinPackage)


class DeviceViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    add the given device ID to user
    """
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
        serializer = self.serializer_class(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def list(self, request):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        UserPage.objects.filter(page=pk, user=request.user).update(is_active=False)
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


class UserInquiryViewSet(viewsets.GenericViewSet):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = UserInquiry.objects.all()
    serializer_class = UserInquirySerializer
    pagination_class = InquiryPagination
    filterset_fields = ['status', 'order__action']

    def get_inquiry(self, request, action_type):
        page_id = request.query_params.get('page_id')
        if not page_id:
            return Response({'Error': _('page_id is required')}, status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = abs(min(int(request.query_params.get('limit', 0)), 100))
        except ValueError:
            raise ValidationError(detail={'detail': _('make sure the limit value is a positive number!')})

        try:
            user_page = UserPage.objects.get(page=page_id, user=self.request.user)
        except UserPage.DoesNotExist:
            raise ValidationError(detail={'detail': _('user and page does not match!')})
        inquiries = CustomService.get_or_create_inquiries(user_page, action_type, limit)

        serializer = self.serializer_class(inquiries, many=True)
        return Response(serializer.data)

    def get_inquiry_report(self, request):
        self.filter_backends = [DjangoFilterBackend]
        inquiries = self.filter_queryset(self.get_queryset())
        inquiries = inquiries.filter(user_page__user=request.user)
        page_id = request.query_params.get('page_id')
        if page_id:
            try:
                user_page = UserPage.objects.get(page=page_id, user=request.user)
                inquiries = inquiries.filter(user_page=user_page)
            except UserPage.DoesNotExist:
                raise ValidationError(detail={'detail': _('user and page does not match!')})
        page = self.paginate_queryset(inquiries.order_by('-created_time'))
        serializer = self.serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)

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

    @action(methods=['get'], detail=False, url_path="report")
    def report(self, request, *args, **kwargs):
        """Get a list of user inquiries report"""
        return self.get_inquiry_report(request)

    @swagger_auto_schema(
        operation_description='Check whether or not the user did the action properly for the order such as (like, comment or follow).',
        method='post',
        request_body=INQUIRY_POST_DOC

    )
    @action(methods=['post'], detail=False)
    def done(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = UserInquiry.objects.filter(id__in=serializer.validated_data['done_ids'])
        queryset.update(status=UserInquiry.STATUS_DONE)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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

    @method_decorator(name='total', decorator=swagger_auto_schema(
        operation_description="Get user total coin balance",
        responses={"200": 'Successful'}
    ))
    @action(methods=['get'], detail=False, url_path='total')
    def total(self, request, *args, **kwargs):
        wallet = self.get_queryset().aggregate(amount=Coalesce(Sum('amount'), 0)).get('amount')
        return Response({'wallet': wallet})


class InstaActionAPIView(generics.ListAPIView):
    """Get a list of action types and their values"""
    queryset = InstaAction.objects.all()
    serializer_class = InstaActionSerializer


class CoinPackageAPIView(generics.ListAPIView):
    """Get a list of coin packages"""
    queryset = CoinPackage.objects.filter(is_enable=True)
    serializer_class = CoinPackageSerializer


class CoinPackagePurchaseAPIView(views.APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        package_name = request.data.get('package_name')
        product_id = request.data.get('product_id')
        purchase_token = request.data.get('purchase_token')
        access_token = request.data.get('access_token')
        if package_name is None:
            raise ValidationError(detail={'detail': _('package name is required!')})
        if product_id is None:
            raise ValidationError(detail={'detail': _('product_id name is required!')})
        if purchase_token is None:
            raise ValidationError(detail={'detail': _('purchase_token name is required!')})
        if access_token is None:
            raise ValidationError(detail={'detail': _('access_token name is required!')})
        iab_base_api = "https://pardakht.cafebazaar.ir/devapi/v2/api"
        iab_api_path = "validate/{}/inapp/{}/purchases/{}/".format(
            package_name,
            product_id,
            purchase_token
        )
        iab_url = "{}/{}".format(iab_base_api, iab_api_path)

        response = requests.get(url=iab_url, params={"access_token": access_token})
        res_json = response.json()
        if response.status_code == 404 and res_json.get("error") == "not_found":
            raise ValidationError(detail={'detail': _('purchase has not been found !')})
        elif response.status_code == 200:
            try:
                package = CoinPackage.objects.get(name=package_name, product_id=product_id)
            except CoinPackage.DoesNotExist:
                raise ValidationError(detail={'detail': _('package does not exists!')})
            CoinTransaction.objects.create(
                user=user,
                amount=package.amount,
                package=package,
                description=_("coin package has been purchased.")
            )
            return Response({'user': user, 'package': package, 'is_valid': True}, status=status.HTTP_200_OK)
