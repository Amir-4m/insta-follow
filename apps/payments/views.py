from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from apps.instagram_app.models import CoinPackageOrder
from apps.payments.models import Gateway


def bazaar_token_view(request, *args, **kwargs):
    return HttpResponse()


class PayView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(PayView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        """
        check id and gateway and redirect user to related paying method
        """
        # check and validate parameters
        if not ('invoice_number' in request.GET or 'gateway' in request.GET):
            return HttpResponse("")

        try:
            gateway = Gateway.objects.get(id=request.GET['gateway'], is_enable=True)
        except Gateway.DoesNotExist:
            return HttpResponse("")

        try:
            payment = CoinPackageOrder.objects.get(invoice_number=request.GET['invoice_number'], is_paid=None)
        except CoinPackageOrder.DoesNotExist:
            return HttpResponse("")

        # assign gateway to payment
        payment.gateway = gateway
        payment.save(update_fields=['gateway'])

        return render_bank_page(
            request,
            payment.invoice_number,
            gateway.gateway_url,
            gateway.merchant_id,
            payment.coin_package.amount,
            ResNum1='fastcharge'
        )


def render_bank_page(request, invoice_id, request_url, merchant_id, amount, phone_number='', **kwargs):
    """
    send parameters to a template ... template contain a form include these parameters
    this form automatically submit to bank url
    """
    render_context = {
        "invoice_id": invoice_id,
        "request_url": request_url,
        "merchant_id": merchant_id,
        "redirect_url": request.build_absolute_uri(reverse('purchase-verification')),
        "amount": amount * 10,
        "extra_data": kwargs,
    }
    return render(request, 'payments/pay.html', context=render_context)
