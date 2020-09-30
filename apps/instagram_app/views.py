import json
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.utils.translation import ugettext_lazy as _

from apps.instagram_app.models import CoinPackageOrder, CoinTransaction


class PaymentView(View):
    def get(self, request, *args, **kwargs):
        invoice_number = request.GET.get('service_reference')
        purchase_verified = request.GET.get('purchase_verified')
        if purchase_verified is None:
            return HttpResponse('وضعیت سفارش نا معتبر می باشد !')

        try:
            order = CoinPackageOrder.objects.get(invoice_number=invoice_number, is_paid=None)
        except CoinPackageOrder.DoesNotExist:
            return HttpResponse('سفارشی یافت نشد !')

        if json.loads(purchase_verified) is True:
            html = 'instagram_app/payment_done.html'
            order.is_paid = purchase_verified
            order.save()

        else:
            html = 'instagram_app/payment_failed.html'

        if order.is_paid is True:
            CoinTransaction.objects.create(
                page=order.page,
                amount=order.coin_package.amount,
                package=order,
                description=_("coin package has been purchased.")
            )
        context = {
            "redirect_url": order.redirect_url,
            "purchase_verified": purchase_verified
        }
        return render(request, html, context)
