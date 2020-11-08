from django.contrib import admin

from .models import AdReward


@admin.register(AdReward)
class AdRewardAdmin(admin.ModelAdmin):
    list_display = ('page', 'ad_unit', 'ad_network', 'reward_amount', 'reward_item', 'created_time')
