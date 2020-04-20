from django.contrib import admin
from .models import Category, InstaPage, UserPage, Package, UserPackage, Order, UserAssignment


@admin.register(Category)
class CategoryModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_time')
    list_filter = ('name',)
    search_fields = ('name',)
    sortable_by = ('-created_time',)


@admin.register(InstaPage)
class InstaPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'instagram_username', 'instagram_user_id', 'category', 'updated_time', 'created_time')
    list_filter = ('category',)
    search_fields = ('instagram_username', 'instagram_user_id')
    sortable_by = ('-created_time',)


@admin.register(UserPage)
class UserPageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'page', 'updated_time', 'created_time')
    sortable_by = ('-created_time',)


@admin.register(Package)
class PackageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_time')
    search_fields = ('name',)
    sortable_by = ('-created_time',)


@admin.register(UserPackage)
class UserPackageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_page', 'package', 'created_time')
    sortable_by = ('-created_time',)


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_package', 'action_type', 'link', 'is_enable', 'created_time')
    list_filter = ('action_type',)
    sortable_by = ('-created_time',)


@admin.register(UserAssignment)
class UserAssignmentModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user_page', 'validated_time ', 'last_check_time', 'updated_time', 'created_time')
    sortable_by = ('-created_time',)
