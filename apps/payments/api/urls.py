from rest_framework import routers

from .views import GatewayViewSet

urlpatterns = []

router = routers.DefaultRouter()
router.register('gateways', GatewayViewSet, basename='gateway')

urlpatterns += router.urls
