import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, generics, mixins, views
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend

from ..authentications import PageAuthentication
from ..swagger_schemas import ORDER_POST_DOCS, INQUIRY_POST_DOC
from .serializers import (
    OrderSerializer,
    UserInquirySerializer,
    CoinTransactionSerializer,
    InstaActionSerializer,
    DeviceSerializer,
    CoinPackageSerializer,
    CoinPackageOrderSerializer,
    LoginVerificationSerializer,
    PurchaseSerializer,
    CommentSerializer,
    CoinTransferSerializer,
    ReportAbuseSerializer,
    PackageOrderGateWaySerializer,
)
from ..services import CustomService
from ..pagination import CoinTransactionPagination, OrderPagination, InquiryPagination
from apps.instagram_app.models import (
    InstaAction, Order, UserInquiry,
    CoinTransaction, Device, CoinPackage,
    CoinPackageOrder, InstaPage, Comment,
    ReportAbuse,
)

logger = logging.getLogger(__name__)


class LoginVerification(generics.CreateAPIView):
    serializer_class = LoginVerificationSerializer
    queryset = InstaPage.objects.all()


class DeviceViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    add the given device ID to user
    """
    serializer_class = DeviceSerializer
    authentication_classes = (PageAuthentication,)
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
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    pagination_class = OrderPagination

    def get_queryset(self):
        qs = super(OrderViewSet, self).get_queryset()
        return qs.filter(owner=self.request.auth['page']).order_by('-created_time')

    def perform_create(self, serializer):
        serializer.save(page=self.request.auth['page'])


class UserInquiryViewSet(viewsets.GenericViewSet):
    authentication_classes = (PageAuthentication,)
    queryset = UserInquiry.objects.all()
    serializer_class = UserInquirySerializer
    pagination_class = InquiryPagination
    filterset_fields = ['status', 'order__action']

    def get_inquiry(self, request, action_type):
        page = request.auth['page']
        try:
            limit = abs(min(int(request.query_params.get('limit', 0)), 100))
        except ValueError:
            raise ValidationError(detail={'detail': _('make sure the limit value is a positive number!')})

        inquiries = CustomService.get_or_create_inquiries(page, action_type, limit)

        serializer = self.serializer_class(inquiries, many=True)
        return Response(serializer.data)

    def get_inquiry_report(self, request):
        self.filter_backends = [DjangoFilterBackend]
        inquiries = self.filter_queryset(self.get_queryset())
        inquiries = inquiries.filter(page=request.auth['page'])
        page_uuid = request.query_params.get('uuid')
        if page_uuid:
            try:
                page = InstaPage.objects.get(uuid=page_uuid)
                inquiries = inquiries.filter(page=page)
            except InstaPage.DoesNotExist:
                raise ValidationError(detail={'detail': _('page does not exists!')})
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
        for obj in queryset:
            obj.status = UserInquiry.STATUS_VALIDATED
            if obj.order.action.action_type in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]:
                obj.validated_time = timezone.now()
                CoinTransaction.objects.create(
                    page=obj.page,
                    inquiry=obj,
                    amount=obj.order.action.action_value,
                    description=f"validated inquiry {obj.id}"
                )
            obj.save()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CoinTransactionAPIView(viewsets.GenericViewSet, mixins.ListModelMixin):
    """Shows a list of user transactions"""
    authentication_classes = (PageAuthentication,)
    queryset = CoinTransaction.objects.all()
    serializer_class = CoinTransactionSerializer
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


class CoinPackageViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """Get a list of coin packages"""
    queryset = CoinPackage.objects.filter(is_enable=True)
    serializer_class = CoinPackageSerializer


class CoinPackageOrderViewSet(
    viewsets.GenericViewSet,
    generics.ListAPIView,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
):
    authentication_classes = (PageAuthentication,)
    queryset = CoinPackageOrder.objects.all()
    serializer_class = CoinPackageOrderSerializer

    def get_queryset(self):
        qs = super(CoinPackageOrderViewSet, self).get_queryset()
        return qs.filter(page=self.request.auth['page'])

    def perform_create(self, serializer):
        serializer.save(page=self.request.auth['page'])


class PurchaseVerificationAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)

    def post(self, request, *args, **kwargs):
        page = request.auth['page']
        purchase_verified = False
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gateway_code = serializer.validated_data['gateway_code']
        purchase_token = serializer.validated_data.get('purchase_token')
        package_order = serializer.validated_data['package_order']
        with transaction.atomic():
            order = CoinPackageOrder.objects.select_related().get(id=package_order.id)
            if gateway_code == "BAZAAR":
                try:
                    response = CustomService.payment_request(
                        'purchase/verify',
                        'post',
                        data={
                            'order_reference': order.invoice_number,
                            'purchase_token': purchase_token
                        }
                    )
                    purchase_verified = response.json()['purchase_verified']
                except Exception as e:
                    logger.error(f"error calling payment with endpoint purchase/verify and action post: {e}")
                    raise ValidationError(detail={'detail': _('error in verifying purchase')})
            elif gateway_code == "SAMAN":
                try:
                    response = CustomService.payment_request(f'orders/{order.invoice_number}', 'get')
                    purchase_verified = response.json()['is_paid']
                except Exception as e:
                    logger.error(
                        f"error calling payment with endpoint orders/{order.invoice_number} and action get: {e}"
                    )
                    raise ValidationError(detail={'detail': _('error in verifying purchase')})

            order.is_paid = purchase_verified
            order.save()

        if order.is_paid is True:
            CoinTransaction.objects.create(
                page=page,
                amount=order.coin_package.amount,
                package=order,
                description=_("coin package has been purchased.")
            )
        return Response({'purchase_verified': purchase_verified})


class CommentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer


class CoinTransferAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)

    def get(self, request, *args, **kwargs):
        page = request.auth['page']
        wallet = page.coin_transactions.all().aggregate(wallet=Coalesce(Sum('amount'), 0))['wallet']
        return Response({'wallet': wallet, 'maximum_amount': settings.MAXIMUM_COIN_TRANSFER})

    def post(self, request, *args, **kwargs):
        page = request.auth['page']
        serializer = CoinTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(sender=page)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReportAbuseViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = ReportAbuse.objects.all()
    serializer_class = ReportAbuseSerializer
    authentication_classes = (PageAuthentication,)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.auth['page'])


class OrderGateWayAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)

    def post(self, request, *args, **kwargs):
        serializer = PackageOrderGateWaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package_order = serializer.validated_data['package_order']
        gateway = serializer.validated_data['gateway']
        try:
            # TODO redirect_url
            CustomService.payment_request(
                'orders',
                'post',
                data={
                    'gateway': gateway,
                    'price': package_order.price,
                    'service_reference': package_order.invoice_number,
                    'is_paid': package_order.is_paid
                }
            )
        except Exception as e:
            logger.error(f"error calling payment with endpoint orders and action post: {e}")
            raise ValidationError(detail={'detail': _('error in submitting order gateway')})

        try:
            response = CustomService.payment_request(
                'purchase/gateway',
                'post',
                data={'order': package_order.invoice_number, 'gateway': gateway}
            )
        except Exception as e:
            logger.error(f"error calling payment with endpoint orders and action post: {e}")
            raise ValidationError(detail={'detail': _('error in getting order gateway')})

        return Response(data={'gateway_url': response.json().get('gateway_url')})
