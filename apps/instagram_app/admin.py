from django.contrib import admin

from .forms import InstagramAccountForm
from .models import (
    InstaPage,
    Order, UserInquiry, InstaAction,
    CoinPackage, CoinPackageOrder,
    Comment, InstagramAccount)


@admin.register(InstaPage)
class InstaPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'instagram_username', 'instagram_user_id', 'updated_time', 'created_time')
    search_fields = ('instagram_username', 'instagram_user_id')
    sortable_by = ('-created_time',)


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'link', 'instagram_username', 'is_enable', 'created_time')
    list_filter = ('action',)
    readonly_fields = ('media_url', 'instagram_username', 'entity_id')
    sortable_by = ('-created_time',)
    search_fields = ('owner__username', 'owner__email')


@admin.register(UserInquiry)
class UserInquiryModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'page', 'status', 'validated_time', 'updated_time', 'created_time')
    list_select_related = ['order', 'page']
    list_filter = ('status',)
    sortable_by = ('-created_time',)
    search_fields = ('page__instagram_username',)


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


@admin.register(Comment)
class CommentModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'updated_time', 'created_time')
