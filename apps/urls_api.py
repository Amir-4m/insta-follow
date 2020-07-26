from django.urls import path, include

urlpatterns = [
    path('accounts/', include("apps.accounts.api.urls")),
    path('instagram/', include("apps.instagram_app.api.urls")),
    path('payments/', include("apps.payments.api.urls"))
]
