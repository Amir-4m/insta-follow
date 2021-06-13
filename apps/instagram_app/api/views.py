import logging

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
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
    InstaActionSerializer, CoinPackageSerializer,
    CoinPackageOrderSerializer, LoginVerificationSerializer, PurchaseSerializer,
    CommentSerializer, CoinTransferSerializer, ReportAbuseSerializer,
    PackageOrderGateWaySerializer,
    TestInstaPageSerializer)
from ..services import CustomService
from ..pagination import CoinTransactionPagination, OrderPagination, CoinPackageOrderPagination
from apps.instagram_app.models import (
    InstaAction, Order, UserInquiry,
    CoinTransaction, CoinPackage,
    CoinPackageOrder, InstaPage, Comment,
    ReportAbuse,
    AllowedGateway
)
from apps.instagram_app.tasks import check_order_validity
from apps.services.api.authentications import ServiceAuthentication
from apps.services.api.permissions import ServicePermission

logger = logging.getLogger(__name__)


class PrivateAccount(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    def get(self, request, *args, **kwargs):
        page = request.auth['page']
        orders = Order.objects.filter(entity_id=page.instagram_user_id, action__action_type=InstaAction.ACTION_FOLLOW,
                                      status=Order.STATUS_ENABLE)
        for order in orders:
            check_order_validity.delay(order.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginVerification(generics.CreateAPIView):
    """verify and create the logged in page"""
    serializer_class = LoginVerificationSerializer
    queryset = InstaPage.objects.all()


class TestInstagramPageAPIView(generics.UpdateAPIView):
    """Update an instapage to testing page"""
    lookup_field = 'instagram_user_id'
    authentication_classes = (ServiceAuthentication,)
    permission_classes = (ServicePermission,)
    serializer_class = TestInstaPageSerializer
    queryset = InstaPage.objects.all()


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="Get a list of user submitted orders",
    responses={"200": 'Successful'}
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="Create an order with a chosen action for the post or profile that user requested",
    request_body=ORDER_POST_DOCS
))
@method_decorator(name='list', decorator=cache_page(60 * 15))  # 15 minutes cache
@method_decorator(name='list', decorator=vary_on_headers('Authorization'))
class OrderViewSet(viewsets.GenericViewSet,
                   mixins.CreateModelMixin,
                   mixins.ListModelMixin):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    pagination_class = OrderPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['is_enable', 'action', 'status']

    def get_queryset(self):
        qs = super(OrderViewSet, self).get_queryset()
        return qs.filter(owner=self.request.auth['page']).order_by('-created_time')

    def perform_create(self, serializer):
        serializer.save(page=self.request.auth['page'])

    def get_orders(self, request, action_type):
        page = request.auth['page']
        try:
            limit = abs(min(int(request.query_params.get('limit', 1)), 100))
        except ValueError:
            raise ValidationError(detail={'detail': _('make sure the limit value is a positive number!')})

        orders = CustomService.get_or_create_orders(page, action_type, limit)

        serializer = self.serializer_class(orders, many=True, context={'request': request})
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


class UserInquiryViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = UserInquiry.objects.select_related('order', 'order__action').all()
    serializer_class = UserInquirySerializer

    @swagger_auto_schema(
        operation_description='Check whether or not the user did the action properly for the order such as (like, comment or follow).',
        method='post',
        request_body=INQUIRY_POST_DOC

    )
    @action(methods=['post'], detail=False)
    def done(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
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


@method_decorator(name='list', decorator=cache_page(60 * 60 * 5))  # 5 hours cache
class InstaActionAPIView(generics.ListAPIView):
    """Get a list of action types and their values"""
    queryset = InstaAction.objects.all()
    serializer_class = InstaActionSerializer


@method_decorator(name='list', decorator=cache_page(60 * 60 * 2))  # 2 hours cache
@method_decorator(name='retrieve', decorator=cache_page(60 * 30))  # 30 minutes cache
class CoinPackageViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    """Get a list of coin packages"""
    queryset = CoinPackage.objects.filter(is_enable=True).order_by('price')
    serializer_class = CoinPackageSerializer


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="Get a list of user created package orders",
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Get a single package order object by passing its ID",
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="Create an order with a chosen coin package for the page requested",
    request_body=PackageOrder_DOC,
    responses={"201": PackageOrder_DOCS_RESPONSE}
))
class CoinPackageOrderViewSet(
    viewsets.GenericViewSet,
    generics.ListAPIView,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = CoinPackageOrder.objects.filter(is_paid=True)
    serializer_class = CoinPackageOrderSerializer
    pagination_class = CoinPackageOrderPagination

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(page=self.request.auth['page']).order_by('-pk')

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
        package_order = serializer.validated_data['package_order']
        with transaction.atomic():
            order = CoinPackageOrder.objects.select_related('coin_package').get(id=package_order.id)
            if gateway_code == "BAZAAR":
                order.reference_id = serializer.validated_data.get('purchase_token', '')
                try:
                    _r = CustomService.payment_request(
                        'purchase/verify',
                        'post',
                        data={
                            'order': str(order.invoice_number),
                            'purchase_token': order.reference_id
                        }
                    )
                    purchase_verified = _r['purchase_verified']
                except Exception as e:
                    order.save()
                    logger.error(f"error calling payment with endpoint purchase/verify and action post: {e}")
                    raise ValidationError(detail={'detail': _('error in verifying purchase')})

            order.is_paid = purchase_verified
            order.save()

        return Response({'purchase_verified': purchase_verified})


@method_decorator(name='list', decorator=cache_page(60 * 60 * 5))  # 5 hours cache
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
        serializer = CoinTransferSerializer(data=request.data, context={'request': request})
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
        request_body=Order_GateWay_DOC,
        responses={"200": ORDER_POST_DOCS_RESPONSE}

    )
    def post(self, request, *args, **kwargs):
        serializer = PackageOrderGateWaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package_order = serializer.validated_data['package_order']
        gateway = serializer.validated_data['gateway']
        code = ''

        for gw in AllowedGateway.get_gateways_by_version_name(package_order.version_name):
            if gw['id'] == gateway:
                package_order.gateway = gw['display_name']
                code = gw['code']
                break

        if not code:
            raise ValidationError(detail={'detail': _('no gateway has been found.')})

        try:
            data = {
                'gateway': gateway,
                'price': package_order.price,
                'service_reference': str(package_order.invoice_number),
                'is_paid': package_order.is_paid,
                "redirect_url": request.build_absolute_uri(reverse('payment-done')),

            }
            if code == 'BAZAAR':
                if not package_order.coin_package.sku:
                    raise ValidationError(detail={'detail': _('coin package has no sku.')})

                data.update({
                    "sku": package_order.coin_package.sku,
                    "package_name": settings.CAFE_BAZAAR_PACKAGE_NAME
                })

            _r = CustomService.payment_request(
                'orders',
                'post',
                data=data
            )
            transaction_id = _r.get('transaction_id')

        except Exception as e:
            logger.error(f"error calling payment with endpoint orders and action post: {e}")
            raise ValidationError(detail={'detail': _('error in submitting order gateway')})

        package_order.transaction_id = transaction_id
        package_order.save()

        try:
            response = CustomService.payment_request(
                'purchase/gateway',
                'post',
                data={'order': str(package_order.invoice_number), 'gateway': gateway}
            )
        except Exception as e:
            logger.error(f"error calling payment with endpoint purchase/gateway and action post: {e}")
            raise ValidationError(detail={'detail': _('error in getting order gateway')})

        return Response(data=response)


class GatewayAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)

    def get(self, request, *args, **kwargs):
        version_name = request.query_params.get('version_name')
        if version_name is None:
            raise ValidationError(detail={'detail': _('version must be set in query params!')})
        gateways_list = AllowedGateway.get_gateways_by_version_name(version_name)

        return Response(gateways_list)


class ScoreBoardApiView(generics.GenericAPIView):
    authentication_classes = (PageAuthentication,)
    permission_classes = (PagePermission,)
    queryset = CoinTransaction.objects.filter(
        transaction_type=CoinTransaction.TYPE_INQUIRY,
        inquiry__validated_time__isnull=False,
        created_time__gte=timezone.now().replace(hour=0, minute=0)
    ).values(
        'page__instagram_user_id',
        'page__instagram_username',
        'page__picture_url'
    ).annotate(
        total=Sum('amount'),
    ).order_by('-total')[:50]

    def get(self, request, *args, **kwargs):
        page = self.request.auth['page']
        score_list = list(self.get_queryset())
        try:
            score_list[0].update({'reward': 1000})
            score_list[1].update({'reward': 700})
            score_list[2].update({'reward': 500})
        except IndexError:
            pass

        for score in score_list[3: 10]:
            score.update({'reward': 300})

        for score in score_list[10: 20]:
            score.update({'reward': 200})

        for score in score_list[20: 50]:
            score.update({'reward': 100})

        data = {
            'score_list': score_list,
            'user_score': page.coin_transactions.filter(
                transaction_type=CoinTransaction.TYPE_INQUIRY,
                inquiry__validated_time__isnull=False,
                created_time__gte=timezone.now().replace(hour=0, minute=0)
            ).aggregate(total=Coalesce(Sum('amount'), 0)).get('total'),
        }
        return Response(data=data)
