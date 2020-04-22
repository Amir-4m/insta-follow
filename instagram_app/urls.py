from django.urls import path, include

urlpatterns = [
    path('api/', include('instagram_app.api.urls')),
]
