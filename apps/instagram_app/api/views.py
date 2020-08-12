import re

from django.conf import settings
from django.db import transaction
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

from apps.payments.services import BazaarService, SamanService

from ..authentications import PageAuthentication
from ..swagger_schemas import ORDER_POST_DOCS, INQUIRY_POST_DOC, PROFILE_POST_DOC
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
    ReportAbuseSerializer
)
from ..services import CustomService
from ..pagination import CoinTransactionPagination, OrderPagination, InquiryPagination
from apps.instagram_app.models import (
    InstaAction, Order, UserInquiry,
    CoinTransaction, Device, CoinPackage,
    CoinPackageOrder, InstaPage, Comment,
    ReportAbuse, BlockedText, BlockWordRegex
)
from ...payments.models import Gateway


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
    operation_description="Get a list of user instagram pages and his/her coin balance",
    responses={"200": 'Successful'}
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    request_body=PROFILE_POST_DOC

))
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
        queryset.update(status=UserInquiry.STATUS_DONE)
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
        return queryset.filter(user=self.request.auth['page']).order_by('-created_time')

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
        serializer = PurchaseSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            invoice_number = serializer.validated_data['invoice_number']
            reference_id = serializer.validated_data['reference_id']
            with transaction.atomic():
                order = CoinPackageOrder.objects.select_related('coin_package').select_for_update().get(
                    invoice_number=invoice_number
                )
                if order.is_paid is False:
                    raise ValidationError(detail={'detail': _('purchase has not been done! submit a new order.')})
                elif order.is_paid is True:
                    raise ValidationError(detail={'detail': _('purchase has been done already!')})

                if order.price != order.coin_package.price:
                    raise ValidationError(detail={'detail': _('purchase is invalid!')})

                if order.gateway.code == Gateway.FUNCTION_BAZAAR:
                    purchase_verified = BazaarService.verify_purchase(
                        order.coin_package.name,
                        order.coin_package.sku,
                        reference_id
                    )
                elif order.gateway.code == Gateway.FUNCTION_SAMAN:
                    order.log = request.data
                    if request.data.get("State", "") != "OK":
                        order.result_code = request.data.get("State", "")
                        order.save(update_fields=['updated_time', 'log', 'result_code'])
                        purchase_verified = False
                    else:
                        order.result_code = request.data.get("State", "")
                        order.user_reference = request.data.get("TRACENO", "")

                        purchase_verified = SamanService().verify_saman(
                            order.gateway.verify_url,
                            reference_id,
                            settings.SAMAN_MERCHANT_ID,
                            order.coin_package.amount
                        )
                order.is_paid = purchase_verified
                order.reference_id = reference_id
                order.save()

                if order.is_paid is True:
                    CoinTransaction.objects.create(
                        page=page,
                        amount=order.coin_package.amount,
                        package=order.coin_package,
                        description=_("coin package has been purchased.")
                    )
            return Response({"invoice_number": invoice_number, "is_verified": order.is_paid})


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


class ValidateTextAPIView(views.APIView):
    authentication_classes = (PageAuthentication,)

    def post(self, request, *args, **kwargs):
        page = request.auth['page']
        text = request.data.get('text', '')
        blocked = False
        regex = BlockWordRegex.objects.all()

        for reg in regex:
            if re.match(fr"{reg.pattern}", text):
                BlockedText.objects.create(text=text, pattern=reg, author=page)
                blocked = True
                break

        return Response({'text': text, 'blocked': blocked})
