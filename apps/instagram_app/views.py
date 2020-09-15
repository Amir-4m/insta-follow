from django.shortcuts import render
from django.views import View


class PaymentView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'instagram_app/payment_done.html')
