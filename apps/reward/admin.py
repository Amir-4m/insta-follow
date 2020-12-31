from django.contrib import admin

from .models import AdReward


@admin.register(AdReward)
class AdRewardAdmin(admin.ModelAdmin):
    list_display = ('page', 'reward_amount', 'created_time')