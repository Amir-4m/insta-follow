from django.urls import path

from .views import TokenObtainPairView, TokenRefreshView, HelloView

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name="token"),
    path('token/refresh/', TokenRefreshView.as_view(), name="token_refresh"),

    path('hello/', HelloView.as_view(), name="hello"),
]
