import logging

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, generics, mixins, views
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema

from ..authentications import PageAuthentication
from ..filterset import CoinTransactionFilterBackend
from ..permissions import PagePermission
from ..swagger_schemas import *
from .serializers import (
    OrderSerializer, UserInquirySerializer, CoinTransactionSerializer,
    InstaActionSerializer, DeviceSerializer, CoinPackageSerializer,
    CoinPackageOrderSerializer, LoginVerificationSerializer, PurchaseSerializer,
    CommentSerializer, CoinTransferSerializer, ReportAbuseSerializer,
    PackageOrderGateWaySerializer,
)
from ..services import CustomService
from ..pagination import CoinTransactionPagination, OrderPagination, InquiryPagination, CoinPackageOrderPagination
from apps.instagram_app.models import (
    InstaAction, Order, UserInquiry,
    CoinTransaction, Device, CoinPackage,
    CoinPackageOrder, InstaPage, Comment,
    ReportAbuse,
    AllowedGateway
)

logger = logging.getLogger(__name__)


class LoginVerification(generics.CreateAPIView):
    """verify and create the logged in page"""
    serializer_class = LoginVerificationSerializer
    queryset = InstaPage.objects.all()


class DeviceViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    add the given device ID to user
    """
    serializer_class = DeviceSerializer
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = Device.objects.all()

    def perform_create(self, serializer):
        serializer.save(page=self.request.auth['page'])


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
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    pagination_class = OrderPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['is_enable', 'action']

    def get_queryset(self):
        qs = super(OrderViewSet, self).get_queryset()
        return qs.filter(owner=self.request.auth['page']).order_by('-created_time')

    def perform_create(self, serializer):
        serializer.save(page=self.request.auth['page'])

    def get_orders(self, request, action_type):
        page = request.auth['page']
        try:
            limit = abs(min(int(request.query_params.get('limit', 0)), 100))
        except ValueError:
            raise ValidationError(detail={'detail': _('make sure the limit value is a positive number!')})

        orders = CustomService.get_or_create_orders(page, action_type, limit)

        serializer = self.serializer_class(orders, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="like")
    def like(self, request, *args, **kwargs):
        """Get a list of like orders that user must like them"""
        return self.get_orders(request, InstaAction.ACTION_LIKE)

    @action(methods=['get'], detail=False, url_path="comment")
    def comment(self, request, *args, **kwargs):
        """Get a list of comment orders that user must comment for them"""
        return self.get_orders(request, InstaAction.ACTION_COMMENT)

    @action(methods=['get'], detail=False, url_path="follow")
    def follow(self, request, *args, **kwargs):
        """Get a list of follow orders that user must follow"""
        return self.get_orders(request, InstaAction.ACTION_FOLLOW)


class UserInquiryViewSet(viewsets.GenericViewSet):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = UserInquiry.objects.all()
    serializer_class = UserInquirySerializer
    pagination_class = InquiryPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['status', 'order__action']

    @swagger_auto_schema(
        operation_description='Check whether or not the user did the action properly for the order such as (like, comment or follow).',
        method='post',
        request_body=INQUIRY_POST_DOC

    )
    @action(methods=['post'], detail=False)
    def done(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        page = self.request.auth['page']
        try:
            order = Order.objects.get(id=serializer.validated_data['done_id'])
        except Order.DoesNotExist:
            raise ValidationError(detail={'detail': _('order with this id does not exist !')})
        user_inquiry, created = UserInquiry.objects.get_or_create(
            order=order,
            page=page,
            defaults=dict(page=page)
        )

        if not created:
            raise ValidationError(detail={'detail': _('order with this id already has been done by this page !')})

        if user_inquiry.order.action.action_type in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]:
            user_inquiry.validated_time = timezone.now()
            if order.owner != page:
                CoinTransaction.objects.create(
                    page=user_inquiry.page,
                    inquiry=user_inquiry,
                    amount=user_inquiry.order.action.action_value,
                    description=_("%s") % user_inquiry.order.action.get_action_type_display())
            user_inquiry.save()

        serializer = self.get_serializer(user_inquiry)
        return Response(serializer.data)


class CoinTransactionAPIView(viewsets.GenericViewSet, mixins.ListModelMixin):
    """Shows a list of user transactions"""
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = CoinTransaction.objects.all()
    serializer_class = CoinTransactionSerializer
    filter_backends = (CoinTransactionFilterBackend,)
    filterset_fields = ['inquiry__order__action', 'order__action']
    pagination_class = CoinTransactionPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(page=self.request.auth['page']).order_by('-created_time')

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


class CoinPackageViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    """Get a list of coin packages"""
    queryset = CoinPackage.objects.filter(is_enable=True)
    serializer_class = CoinPackageSerializer


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="Get a list of user created package orders",
    responses={"200": 'Successful'}
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Get a single package order object by passing its ID",
    responses={"200": 'Successful'}
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="Create an order with a chosen coin package for the page requested",
    request_body=PackageOrder_DOC
))
class CoinPackageOrderViewSet(
    viewsets.GenericViewSet,
    generics.ListAPIView,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = CoinPackageOrder.objects.all()
    serializer_class = CoinPackageOrderSerializer
    pagination_class = CoinPackageOrderPagination

    def get_queryset(self):
        qs = super(CoinPackageOrderViewSet, self).get_queryset()
        return qs.filter(page=self.request.auth['page']).order_by('-created_time')

    def perform_create(self, serializer):
        serializer.save(page=self.request.auth['page'])


class PurchaseVerificationAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @swagger_auto_schema(operation_description='Verify user purchase with bank or psp', request_body=PURCHASE_DOC)
    def post(self, request, *args, **kwargs):
        page = request.auth['page']
        purchase_verified = False
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gateway_code = serializer.validated_data['gateway_code']
        purchase_token = serializer.validated_data.get('purchase_token')
        package_order = serializer.validated_data['package_order']
        with transaction.atomic():
            order = CoinPackageOrder.objects.select_related('coin_package').get(id=package_order.id)
            if gateway_code == "BAZAAR":
                try:
                    response = CustomService.payment_request(
                        'purchase/verify',
                        'post',
                        data={
                            'order': str(order.invoice_number),
                            'purchase_token': purchase_token
                        }
                    )
                    purchase_verified = response.json()['purchase_verified']
                except Exception as e:
                    logger.error(f"error calling payment with endpoint purchase/verify and action post: {e}")
                    raise ValidationError(detail={'detail': _('error in verifying purchase')})

            order.is_paid = purchase_verified
            order.save()

        if order.is_paid is True:
            coin_package = order.coin_package
            ct_amount = coin_package.amount if coin_package.amount_offer is None else coin_package.amount_offer

            CoinTransaction.objects.create(
                page=page,
                amount=ct_amount,
                package=order,
                description=_("coin package has been purchased.")
            )
        return Response({'purchase_verified': purchase_verified})


class CommentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """Shows a list of pre-defined comments"""
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer


class CoinTransferAPIView(views.APIView):
    """
    API for transfer coin from a page to another, based on a pre-defined maximum amount
    """
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @swagger_auto_schema(operation_description='shows the allowed maximum amount to transfer', )
    def get(self, request, *args, **kwargs):
        page = request.auth['page']
        wallet = page.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0))['wallet']
        return Response({
            'wallet': wallet,
            'maximum_amount': settings.MAXIMUM_COIN_TRANSFER,
            'fee_amount': settings.COIN_TRANSFER_FEE
        })

    @swagger_auto_schema(
        operation_description='transfer coin from the current logged in page to another',
        request_body=TRANSFER_COIN_DOC
    )
    def post(self, request, *args, **kwargs):
        page = request.auth['page']
        serializer = CoinTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(sender=page)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="create a abuser report for an order",
    request_body=REPORT_ABUSE_DOC
))
class ReportAbuseViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = ReportAbuse.objects.all()
    serializer_class = ReportAbuseSerializer
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.auth['page'])


class OrderGateWayAPIView(views.APIView):
    """Set an gateway for a package order to get the payment url"""
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @swagger_auto_schema(
        operation_description='Set an gateway for a package order to get the payment url',
        request_body=Order_GateWay_DOC

    )
    def post(self, request, *args, **kwargs):
        serializer = PackageOrderGateWaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package_order = serializer.validated_data['package_order']
        gateway = serializer.validated_data['gateway']
        sku = None
        if package_order.coin_package.sku is not None:
            sku = package_order.coin_package.sku
        try:

            order_response = CustomService.payment_request(
                'orders',
                'post',
                data={
                    'gateway': gateway,
                    'price': package_order.price,
                    'service_reference': str(package_order.invoice_number),
                    'is_paid': package_order.is_paid,
                    "properties": {
                        "redirect_url": request.build_absolute_uri(reverse('payment-done')),
                        "sku": sku,
                        "package_name": settings.CAFE_BAZAAR_PACKAGE_NAME
                    }
                }
            )
            CoinPackageOrder.objects.select_for_update(of=('self',))
            transaction_id = order_response.json().get('transaction_id')
            package_order.transaction_id = transaction_id
            package_order.save()
        except Exception as e:
            logger.error(f"error calling payment with endpoint orders and action post: {e}")
            raise ValidationError(detail={'detail': _('error in submitting order gateway')})

        try:
            response = CustomService.payment_request(
                'purchase/gateway',
                'post',
                data={'order': str(package_order.invoice_number), 'gateway': gateway}
            )
        except Exception as e:
            logger.error(f"error calling payment with endpoint orders and action post: {e}")
            raise ValidationError(detail={'detail': _('error in getting order gateway')})

        return Response(data=response.json())


class GatewayAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    def get(self, request, *args, **kwargs):
        version_name = request.query_params.get('version_name')
        if version_name is None:
            raise ValidationError(detail={'detail': _('version must be set in query params!')})

        gateways_list = []
        try:
            response = CustomService.payment_request('gateways', 'get')
            data = response.json()
            allowed_gateways = AllowedGateway.objects.get(version_name=version_name)
            for gateway in data:
                if gateway['code'] in allowed_gateways.gateways_code:
                    gateways_list.append(gateway)

        except AllowedGateway.DoesNotExist as e:
            logger.error(f"error calling payment with endpoint gateways/ and action get: {e}")
            raise ValidationError(detail={'detail': _('no allowed gateway found!')})

        except Exception as e:
            logger.error(f"error calling payment with endpoint gateways/ and action get: {e}")
            gateways_list.clear()
            raise ValidationError(detail={'detail': _('error in getting gateway')})
        return Response(gateways_list)


class DailyRewardAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    @swagger_auto_schema(
        operation_description='Reward page daily with a specific amount of coins',
        responses={200: DAILY_REWARD_DOCS_RESPONSE}
    )
    def get(self, request, *args, **kwargs):
        page = request.auth['page']
        reward_amount = settings.COIN_DAILY_REWARD_AMOUNT
        if CoinTransaction.objects.filter(
                created_time__gte=timezone.now().replace(hour=0, minute=0, second=0),
                description=_("daily reward"),
                page=page
        ).exists():
            rewarded = False
        else:
            CoinTransaction.objects.filter(
            )
            CoinTransaction.objects.create(
                page=page,
                description=_("daily reward"),
                amount=reward_amount
            )
            rewarded = True
        return Response({'page': page.instagram_username, 'amount': reward_amount, 'rewarded': rewarded})
