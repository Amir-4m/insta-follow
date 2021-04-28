from django.contrib import admin
from django.http import HttpResponseRedirect

from apps.services.models import Service
from apps.services.utils import random_secret_generator


@admin.register(Service)
class ServiceModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_enable', 'created_time', 'updated_time')
    list_filter = ('is_enable',)
    readonly_fields = ('secret_key',)
    change_form_template = "services/admin/change-form.html"

    def response_change(self, request, obj):
        if "change-secret" in request.POST:
            key = random_secret_generator()
            while Service.objects.filter(secret_key=key).exists():
                key = random_secret_generator()

            obj.secret_key = key
            obj.save()
            return HttpResponseRedirect(".")  # stay on the same detail page

        return super().response_change(request, obj)
