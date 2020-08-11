from django.urls import path
from .views import bazaar_token_view, PayView
urlpatterns = [
    path('bazaar-token/', bazaar_token_view, name='bazaar-token'),
    path('gateway/', PayView.as_view(), name='payment-gateway')

]
