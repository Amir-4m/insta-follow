from django.contrib import admin

from apps.payments.models import Gateway


@admin.register(Gateway)
class GatewayModelAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'title', 'created_time', 'updated_time')
