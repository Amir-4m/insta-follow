from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from apps.instagram_app.models import CoinPackageOrder


class PaymentView(View):
    def get(self, request, *args, **kwargs):
        invoice_number = request.GET.get('service_reference')
        purchase_verified = request.GET.get('purchase_verified')
        try:
            order = CoinPackageOrder.objects.get(invoice_number=invoice_number)
        except CoinPackageOrder.DoesNotExist:
            return HttpResponse('')

        context = {
            "redirect_url": order.redirect_url,
            "purchase_verified": purchase_verified
        }
        return render(request, 'instagram_app/payment_done.html', context)
