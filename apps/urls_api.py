from django.urls import path, include

urlpatterns = [
    path('instagram/', include("apps.instagram_app.api.urls")),
    path('config/', include("apps.config.api.urls"))
]
