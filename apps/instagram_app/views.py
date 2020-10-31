import json
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.utils.translation import ugettext_lazy as _

from apps.instagram_app.models import CoinPackageOrder, CoinTransaction


class PaymentView(View):
    def get(self, request, *args, **kwargs):
        transaction_id = request.GET.get('transaction_id')
        purchase_verified = request.GET.get('purchase_verified')
        if purchase_verified is None:
            return HttpResponse('وضعیت سفارش نا معتبر می باشد !')

        purchase_verified = purchase_verified.lower().strip()

        try:
            order = CoinPackageOrder.objects.select_related('coin_package').get(
                transaction_id=transaction_id,
                is_paid=None
            )
        except CoinPackageOrder.DoesNotExist:
            return HttpResponse('سفارشی یافت نشد !')

        if purchase_verified == 'true':
            html = 'instagram_app/payment_done.html'
            order.is_paid = True

        else:
            html = 'instagram_app/payment_failed.html'
            order.is_paid = False

        order.save()
        if order.is_paid is True:
            coin_package = order.coin_package
            ct_amount = coin_package.amount if coin_package.amount_offer is None else coin_package.amount_offer
            CoinTransaction.objects.create(
                page=order.page,
                amount=ct_amount,
                package=order,
                description=_("coin package has been purchased.")
            )
        context = {
            "redirect_url": order.redirect_url,
            "purchase_verified": purchase_verified
        }
        return render(request, html, context)
