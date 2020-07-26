from django.urls import path
from .views import bazaar_token_view
urlpatterns = [
    path('bazaar-token/', bazaar_token_view, name='bazaar-token'),
]
