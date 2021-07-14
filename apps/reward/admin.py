from django.contrib import admin

from .models import AdReward, GiftCode


@admin.register(AdReward)
class AdRewardAdmin(admin.ModelAdmin):
    list_display = ('page', 'reward_amount', 'created_time')
    search_fields = ('page__instagram_username',)
    raw_id_fields = ('page', )


@admin.register(GiftCode)
class GiftCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'amount', 'created_time')
    search_fields = ('page__instagram_username', 'code')
    readonly_fields = ['page', 'created_time', 'updated_time']

