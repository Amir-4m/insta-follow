from django.contrib import admin
from .models import Category, InstaPage, UserPage, Order, UserInquiry, InstaAction, CoinTransaction, CoinPackage


@admin.register(Category)
class CategoryModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_time')
    list_filter = ('name',)
    search_fields = ('name',)
    sortable_by = ('-created_time',)


@admin.register(InstaPage)
class InstaPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'instagram_username', 'instagram_user_id', 'updated_time', 'created_time')
    list_filter = ('category',)
    search_fields = ('instagram_username', 'instagram_user_id')
    sortable_by = ('-created_time',)


@admin.register(UserPage)
class UserPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'page', 'updated_time', 'created_time')
    list_select_related = ['user', 'page']
    sortable_by = ('-created_time',)


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'link', 'instagram_username', 'is_enable', 'created_time')
    list_filter = ('action',)
    readonly_fields = ('media_url', 'instagram_username', 'entity_id')
    sortable_by = ('-created_time',)


@admin.register(UserInquiry)
class UserAssignmentModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user_page', 'last_check_time', 'updated_time', 'created_time')
    list_select_related = ['order', 'user_page']
    sortable_by = ('-created_time',)


@admin.register(InstaAction)
class InstaActionModelAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'action_value', 'buy_value', 'updated_time')


@admin.register(CoinPackage)
class CoinPackageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'price', 'updated_time', 'created_time')
    sortable_by = ('-created_time', 'price')


@admin.register(CoinTransaction)
class AA(admin.ModelAdmin):
    pass
