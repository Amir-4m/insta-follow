from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

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
    search_fields = ('instagram_username', 'instagram_user_id', 'device_uuids',)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = (
        'instagram_username', 'id', 'action', 'link', 'target_no',
        'status', 'achieved_number_approved', 'created_time'
    )
    list_filter = ('action', 'status')
    readonly_fields = ('media_properties', 'instagram_username', 'entity_id', 'achieved_number_approved')
    search_fields = ('owner__instagram_username', 'id', 'link')
    raw_id_fields = ('owner',)
    date_hierarchy = 'created_time'

    def has_add_permission(self, request):
        return False


@admin.register(UserInquiry)
class UserInquiryModelAdmin(admin.ModelAdmin):
    list_display = ('order', 'page', 'status', 'validated_time', 'updated_time', 'created_time')
    list_select_related = ['order', 'page']
    readonly_fields = ('validated_time', 'page', 'order')
    list_filter = ('status', 'order__action')
    search_fields = ('page__instagram_username',)
    raw_id_fields = ('order', 'page',)
    date_hierarchy = 'created_time'


@admin.register(InstaAction)
class InstaActionModelAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'action_value', 'buy_value', 'updated_time')


@admin.register(CoinPackage)
class CoinPackageModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'price', 'is_featured', 'updated_time', 'created_time')


@admin.register(InstagramAccount)
class InstagramAccountModelAdmin(admin.ModelAdmin):
    form = InstagramAccountForm
    list_display = ('username', 'is_enable', 'updated_time', 'created_time')
    readonly_fields = ('login_attempt',)
    search_fields = ('username',)
    list_filter = ('is_enable',)


def make_paid(modeladmin, request, queryset):
    for obj in queryset.filter(is_paid__isnull=True):
        obj.is_paid = True
        obj.save()


make_paid.short_description = _("Mark selected orders as paid")


@admin.register(CoinPackageOrder)
class CoinPackageOrderModelAdmin(admin.ModelAdmin):
    list_display = (
        'coin_package', 'page', 'price', 'invoice_number', 'transaction_id',
        'reference_id', 'gateway', 'is_paid', 'updated_time', 'created_time'
    )
    list_filter = ('is_paid', 'coin_package', 'gateway')
    search_fields = ('page__instagram_username', 'invoice_number', 'transaction_id', 'reference_id')
    raw_id_fields = ('page',)
    actions = (
        make_paid,
    )
    date_hierarchy = 'created_time'

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Comment)
class CommentModelAdmin(admin.ModelAdmin):
    list_display = ('text', 'updated_time', 'created_time')


@admin.register(ReportAbuse)
class ReportAbuseModelAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'text', 'abuser', 'status', 'created_time')
    list_filter = ('status',)
    raw_id_fields = ('reporter', 'abuser',)

    def save_model(self, request, obj, form, change):
        if obj.status == ReportAbuse.STATUS_APPROVED:
            Order.objects.filter(id=obj.abuser.id).update(status=Order.STATUS_DISABLE,
                                                          description="(Abuse) - The page is disabled due to abuse")
        return super(ReportAbuseModelAdmin, self).save_model(request, obj, form, change)


@admin.register(BlockWordRegex)
class BlockWordRegexModelAdmin(admin.ModelAdmin):
    list_display = ('pattern', 'updated_time', 'created_time')


@admin.register(BlockedText)
class BlockedTextModelAdmin(admin.ModelAdmin):
    list_display = ('text', 'pattern', 'author', 'created_time')
    raw_id_fields = ('author',)


@admin.register(AllowedGateway)
class AllowedGatewayAdmin(admin.ModelAdmin):
    list_display = ('version_pattern', 'gateways_code')
    search_fields = ('version_name', 'gateways_code')


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ('page', 'amount', 'transaction_type', 'created_time')
    search_fields = ('page__instagram_username',)
    list_filter = ('transaction_type',)
    raw_id_fields = ('page', 'inquiry', 'order', 'from_page', 'to_page',)
    date_hierarchy = 'created_time'

    def has_change_permission(self, request, obj=None):
        return False
