from django.contrib import admin

from .forms import InstagramAccountForm
from .models import (
    InstaPage,
    Order, UserInquiry, InstaAction,
    CoinPackage, CoinPackageOrder,
    Comment, InstagramAccount,
    ReportAbuse, BlockWordRegex,
    BlockedText, AllowedGateway, CoinTransaction
)


@admin.register(InstaPage)
class InstaPageModelAdmin(admin.ModelAdmin):
    list_display = ('instagram_username', 'instagram_user_id', 'updated_time', 'created_time')
    readonly_fields = ('uuid',)
    search_fields = ('instagram_username', 'instagram_user_id')
    sortable_by = ('-created_time',)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = ('action', 'link', 'instagram_username', 'is_enable', 'achieved_number_approved', 'created_time')
    list_filter = ('action',)
    readonly_fields = ('media_properties', 'instagram_username', 'entity_id', 'achieved_number_approved')
    sortable_by = ('-created_time',)
    search_fields = ('owner__username', 'owner__email')

    def has_change_permission(self, request, obj=None):
        return True if request.user.is_superuser else False


@admin.register(UserInquiry)
class UserInquiryModelAdmin(admin.ModelAdmin):
    list_display = ('order', 'page', 'status', 'validated_time', 'updated_time', 'created_time')
    list_select_related = ['order', 'page']
    list_filter = ('status', 'order__action')
    sortable_by = ('-created_time',)
    search_fields = ('page__instagram_username',)


@admin.register(InstaAction)
class InstaActionModelAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'action_value', 'buy_value', 'updated_time')


@admin.register(CoinPackage)
class CoinPackageModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'price', 'updated_time', 'created_time')
    sortable_by = ('-created_time', 'price')


@admin.register(InstagramAccount)
class InstagramAccountModelAdmin(admin.ModelAdmin):
    form = InstagramAccountForm
    list_display = ('username', 'is_enable', 'updated_time', 'created_time')
    readonly_fields = ('login_attempt',)
    search_fields = ('username',)
    list_filter = ('is_enbale',)


@admin.register(CoinPackageOrder)
class CoinPackageOrderModelAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'is_paid', 'updated_time', 'created_time')
    list_filter = ('is_paid',)

    def has_change_permission(self, request, obj=None):
        return True if request.user.is_superuser else False


@admin.register(Comment)
class CommentModelAdmin(admin.ModelAdmin):
    list_display = ('text', 'updated_time', 'created_time')


@admin.register(ReportAbuse)
class ReportAbuseModelAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'text', 'abuser', 'status', 'created_time')
    list_filter = ('status',)

    def save_model(self, request, obj, form, change):
        if obj.status == ReportAbuse.STATUS_APPROVED:
            Order.objects.filter(id=obj.abuser.id).update(is_enable=False)
        return super(ReportAbuseModelAdmin, self).save_model(request, obj, form, change)


@admin.register(BlockWordRegex)
class BlockWordRegexModelAdmin(admin.ModelAdmin):
    list_display = ('pattern', 'updated_time', 'created_time')


@admin.register(BlockedText)
class BlockedTextModelAdmin(admin.ModelAdmin):
    list_display = ('text', 'pattern', 'author', 'created_time')


@admin.register(AllowedGateway)
class AllowedGatewayAdmin(admin.ModelAdmin):
    list_display = ('id', 'version_name', 'gateways_code')
    search_fields = ('version_name', 'gateways_code')
    list_filter = ('gateways_code',)


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ('page', 'amount', 'created_time')

    def has_change_permission(self, request, obj=None):
        return False
