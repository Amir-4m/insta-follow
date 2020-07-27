from django.contrib import admin

from .forms import InstagramAccountForm
from .models import (
    InstaPage, UserPage,
    Order, UserInquiry, InstaAction,
    CoinPackage, InstagramAccount, CoinPackageOrder
)


@admin.register(InstaPage)
class InstaPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'instagram_username', 'instagram_user_id', 'updated_time', 'created_time')
    search_fields = ('instagram_username', 'instagram_user_id')
    sortable_by = ('-created_time',)


@admin.register(UserPage)
class UserPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'page', 'updated_time', 'created_time')
    list_select_related = ['user', 'page']
    sortable_by = ('-created_time',)
    search_fields = ('user__username', 'user__email')


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'link', 'instagram_username', 'is_enable', 'created_time')
    list_filter = ('action',)
    readonly_fields = ('media_url', 'instagram_username', 'entity_id')
    sortable_by = ('-created_time',)
    search_fields = ('owner__username', 'owner__email')


@admin.register(UserInquiry)
class UserInquiryModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user_page', 'status', 'validated_time', 'updated_time', 'created_time')
    list_select_related = ['order', 'user_page']
    list_filter = ('status',)
    sortable_by = ('-created_time',)
    search_fields = ('user_page__user__username', 'user_page__user__email')


@admin.register(InstaAction)
class InstaActionModelAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'action_value', 'buy_value', 'updated_time')


@admin.register(CoinPackage)
class CoinPackageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'price', 'updated_time', 'created_time')
    sortable_by = ('-created_time', 'price')


@admin.register(InstagramAccount)
class InstagramAccountModelAdmin(admin.ModelAdmin):
    form = InstagramAccountForm
    list_display = ('id', 'username', 'updated_time', 'created_time')
    readonly_fields = ('login_attempt',)
    search_fields = ('username',)


@admin.register(CoinPackageOrder)
class CoinPackageOrderModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice_number', "transaction_id", 'updated_time', 'created_time')
