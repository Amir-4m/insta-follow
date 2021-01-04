import logging
import uuid

from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

logger = logging.getLogger(__name__)


class InstagramAccount(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    username = models.CharField(_("username"), max_length=120)
    password = models.CharField(_("password"), max_length=250)
    login_attempt = models.IntegerField(_('login attempt'), default=0)
    is_enable = models.BooleanField(_("is enable"), default=True)

    class Meta:
        verbose_name = _("Instagram Account")
        verbose_name_plural = _("Instagram Accounts")


class InstaAction(models.Model):
    ACTION_LIKE = 'L'
    ACTION_FOLLOW = 'F'
    ACTION_COMMENT = 'C'

    ACTION_CHOICES = [
        (ACTION_LIKE, _('Like')),
        (ACTION_FOLLOW, _('Follow')),
        (ACTION_COMMENT, _('Comment')),
    ]
    action_type = models.CharField(_('action type'), max_length=10, choices=ACTION_CHOICES, primary_key=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    action_value = models.PositiveSmallIntegerField(_('action value'))
    buy_value = models.PositiveSmallIntegerField(_('buying value'))

    class Meta:
        db_table = "insta_actions"
        verbose_name = _("Insta Action")
        verbose_name_plural = _("Insta Actions")

    def __str__(self):
        return self.action_type

    def clean(self):
        if self.action_value >= self.buy_value:
            raise ValidationError(_('action value must be lower than buy value'))


class InstaPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    instagram_username = models.CharField(_("instagram username"), max_length=50)
    instagram_user_id = models.BigIntegerField(_("instagram id"), unique=True)
    session_id = models.CharField(_('session id'), max_length=50)

    class Meta:
        db_table = "insta_pages"
        verbose_name = _("Insta Page")
        verbose_name_plural = _("Insta Pages")

    def __str__(self):
        return self.instagram_username


class Device(models.Model):
    page = models.ForeignKey(InstaPage, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(_('device id'), max_length=40, db_index=True)

    class Meta:
        db_table = "insta_devices"
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")

    def __str__(self):
        return f"{self.page.instagram_username} - {self.device_id}"


class Comment(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    text = models.TextField(_("comment text"), max_length=1024)

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")


# Inventory
class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    action = models.ForeignKey(InstaAction, on_delete=models.PROTECT, verbose_name=_('action type'))
    target_no = models.IntegerField(_("target number"), validators=[MinValueValidator(1)])
    link = models.URLField(_("link"))
    media_properties = JSONField(_('media properties'), default=dict)
    entity_id = models.BigIntegerField(_('entity ID'), null=True, db_index=True)
    instagram_username = models.CharField(_("instagram username"), max_length=120)
    comments = ArrayField(models.TextField(max_length=1024), null=True, blank=True)
    description = models.TextField(_("description"), blank=True, default=_('order enabled properly.'))
    is_enable = models.BooleanField(_("is enable"), default=True)
    owner = models.ForeignKey(InstaPage, related_name='orders', on_delete=models.CASCADE)
    track_id = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = "insta_orders"
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"{self.id} - {self.action}"

    def achieved_number_approved(self):
        return UserInquiry.objects.filter(
            order=self,
            status=UserInquiry.STATUS_VALIDATED,
            # validated_time__isnull=False,
        ).count()

    def clean(self):
        if self.action in [InstaAction.ACTION_FOLLOW, InstaAction.ACTION_LIKE] and self.comments is not None:
            raise ValidationError(_("Comment is not allowed in like and follow method!"))


class UserInquiry(models.Model):
    STATUS_VALIDATED = 0
    STATUS_REJECTED = 1

    STATUS_CHOICES = [
        (STATUS_VALIDATED, _('Validated')),
        (STATUS_REJECTED, _('Rejected')),
    ]
    created_time = models.DateTimeField(_("created time"), auto_now_add=True, db_index=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)

    status = models.PositiveSmallIntegerField(_('status'), choices=STATUS_CHOICES, default=STATUS_VALIDATED,
                                              db_index=True)
    validated_time = models.DateTimeField(_("validated time"), null=True, blank=True, db_index=True)

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='user_inquiries')
    page = models.ForeignKey(InstaPage, on_delete=models.CASCADE)

    class Meta:
        db_table = "insta_inquiries"
        verbose_name = _("User Inquiry")
        verbose_name_plural = _('User Inquiries')
        unique_together = ('order', 'page')

    def __str__(self):
        return f"inquiry {self.id}"


class CoinPackage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    amount = models.PositiveIntegerField(_('amount'))
    amount_offer = models.PositiveIntegerField(_('amount offer'), null=True, blank=True)
    price = models.PositiveIntegerField(_('price'))
    price_offer = models.PositiveIntegerField(_('price offer'), null=True, blank=True)
    name = models.CharField(_('package title'), max_length=100, blank=True)
    sku = models.CharField(_('package sku'), max_length=40, unique=True, null=True)
    featured = models.DateTimeField(null=True, blank=True)
    is_enable = models.BooleanField(default=True)

    class Meta:
        db_table = "insta_coin_packages"
        verbose_name = _("Coin Package")
        verbose_name_plural = _('Coin Packages')

    def __str__(self):
        return f"{self.name} - {self.id}"

    @property
    def package_price(self):
        return self.price_offer or self.price

    @property
    def package_amount(self):
        return self.amount_offer or self.price

    def clean(self):
        if self.amount_offer is not None and self.price_offer is not None:
            raise ValidationError(_("You could not set both price offer and amount offer!"))
        if self.amount_offer is not None and self.amount_offer <= self.amount:
            raise ValidationError(_("Amount offer should not be lower than real amount!"))
        if self.price_offer is not None and self.price_offer >= self.price:
            raise ValidationError(_("Price offer should not be higher than real price!"))


class CoinPackageOrder(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    invoice_number = models.UUIDField(_('uuid'), unique=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(_('transaction id'), unique=True, null=True, max_length=40)
    coin_package = models.ForeignKey(CoinPackage, on_delete=models.PROTECT)
    page = models.ForeignKey(InstaPage, on_delete=models.PROTECT, related_name='package_orders')
    is_paid = models.BooleanField(_("is paid"), null=True)
    price = models.PositiveIntegerField(_('price'))
    version_name = models.CharField(_('version name'), max_length=50)
    redirect_url = models.CharField(_('redirect url'), max_length=120)

    class Meta:
        verbose_name = _("Coin Package Order")
        verbose_name_plural = _('Coin Package Orders')

    def __str__(self):
        return f"order {self.id}"


class CoinTransaction(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    page = models.ForeignKey(InstaPage, related_name='coin_transactions', on_delete=models.CASCADE)
    amount = models.IntegerField(_('amount'))
    description = models.TextField(_("description"), blank=True)
    inquiry = models.ForeignKey(UserInquiry, on_delete=models.CASCADE, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    package = models.ForeignKey(CoinPackageOrder, on_delete=models.PROTECT, null=True, blank=True)
    from_page = models.ForeignKey(InstaPage, related_name='senders', on_delete=models.PROTECT, null=True, blank=True)
    to_page = models.ForeignKey(InstaPage, related_name='receivers', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        db_table = "insta_transactions"
        verbose_name = _("Coin Transaction")
        verbose_name_plural = _('Coin Transactions')

    def __str__(self):
        return f"{self.page.instagram_username} - {self.amount}"


class ReportAbuse(models.Model):
    STATUS_OPEN = 'OPEN'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_OPEN, _('Open')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
    ]
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    reporter = models.ForeignKey(InstaPage, related_name='reports', on_delete=models.CASCADE)
    text = models.TextField(_("report text"), max_length=1024)
    abuser = models.ForeignKey(Order, related_name='reports', on_delete=models.PROTECT)
    status = models.CharField(max_length=8, blank=False, choices=STATUS_CHOICES, default=STATUS_OPEN)

    class Meta:
        verbose_name = _("Report Abuse")
        verbose_name_plural = _('Report Abuses')


class BlockWordRegex(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    pattern = models.CharField(_("pattern"), max_length=120)

    class Meta:
        verbose_name = _("Block Word Regex")
        verbose_name_plural = _('Block Word Regex')


class BlockedText(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    text = models.TextField(_('blocked text'))
    pattern = models.ForeignKey(BlockWordRegex, on_delete=models.PROTECT, related_name='blocked_texts')
    author = models.ForeignKey(InstaPage, related_name='blocked_texts', on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Blocked Text")
        verbose_name_plural = _('Blocked Texts')


class AllowedGateway(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    version_name = models.CharField(_('version_name'), max_length=50, unique=True)
    gateways_code = ArrayField(models.CharField(verbose_name=_('code'), max_length=10))

    class Meta:
        verbose_name = _("Allowed Gateway")
        verbose_name_plural = _('Allowed Gateways')
