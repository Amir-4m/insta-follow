from django.urls import path

from .views import PaymentView

urlpatterns = [
    path('payment/done/', PaymentView.as_view(), name='payment-done'),
]
