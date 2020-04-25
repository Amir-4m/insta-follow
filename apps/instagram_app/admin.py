from django.contrib import admin
from .models import Category, InstaPage, UserPage, Package, UserPackage, Order, UserInquiry


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


@admin.register(Package)
class PackageModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'follow_target_no', 'like_target_no',
        'comment_target_no', 'coins', 'is_enable'
    )
    search_fields = ('name',)
    sortable_by = ('-created_time',)


@admin.register(UserPackage)
class UserPackageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'package', 'created_time')
    list_select_related = ['user']
    sortable_by = ('-created_time',)


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_package', 'action_type', 'link', 'is_enable', 'created_time')
    list_filter = ('action_type',)
    list_select_related = ['user_package']
    sortable_by = ('-created_time',)


@admin.register(UserInquiry)
class UserAssignmentModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user_page', 'last_check_time', 'updated_time', 'created_time')
    list_select_related = ['order', 'user_page']
    sortable_by = ('-created_time',)
