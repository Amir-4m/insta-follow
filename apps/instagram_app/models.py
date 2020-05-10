import logging

from django.core.exceptions import ValidationError
from django.db import models, connection
from django.utils.translation import ugettext_lazy as _
from djongo import models as djongo_models

logger = logging.getLogger(__name__)


class Category(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    name = models.CharField(_("category name"), max_length=100, unique=True)

    class Meta:
        db_table = "categories"

    def __str__(self):
        return f"{self.name}"


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

    def __str__(self):
        return self.action_type

    def clean(self):
        if self.action_value > self.buy_value:
            raise ValidationError(_('action value must be lower than buy value'))


class InstaPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    instagram_username = models.CharField(_("instagram username"), max_length=50)
    instagram_user_id = models.BigIntegerField(_("instagram id"), unique=True)
    followers = models.IntegerField(_("page followers"), null=True)
    following = models.IntegerField(_("page following"), null=True)
    post_no = models.IntegerField(_("posts number"), null=True)
    is_banned = models.BooleanField(_("is banned"), default=False)

    category = models.ManyToManyField(Category)
    owner = models.ManyToManyField("accounts.User", through='UserPage', related_name='insta_pages')

    class Meta:
        db_table = "insta_pages"

    def __str__(self):
        return self.instagram_username


class UserPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey("accounts.User", related_name='user_pages', on_delete=models.CASCADE)
    page = models.ForeignKey(InstaPage, related_name='user_pages', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "insta_user_pages"
        unique_together = ['user', 'page']

    def __str__(self):
        return f"{self.user.username} with instagram page {self.page.instagram_username}"


# Inventory
class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    entity_id = models.IntegerField(_('entity ID'), null=True, db_index=True)
    action = models.ForeignKey(InstaAction, on_delete=models.PROTECT, verbose_name=_('action type'))
    target_no = models.IntegerField(_("target number"))
    link = models.URLField(_("link"))
    media_url = models.TextField(_("media url"), blank=True)
    instagram_username = models.CharField(_("instagram username"), max_length=120, blank=True)
    description = models.TextField(_("description"), blank=True, default='')
    is_enable = models.BooleanField(_("is enable"), default=True)
    owner = models.ForeignKey('accounts.User', related_name='user_orders', on_delete=models.CASCADE)

    class Meta:
        db_table = "insta_orders"

    def __str__(self):
        return f"{self.id} - {self.action}"

    def achieved_number_unapproved(self):
        return UserInquiry.objects.filter(
            order=self,
            status=UserInquiry.STATUS_DONE,
            done_time__isnull=False,
        ).count()

    def achieved_number_approved(self):
        return UserInquiry.objects.filter(
            order=self,
            status=UserInquiry.STATUS_VALIDATED,
            validated_time__isnull=False,
        ).count()


class UserInquiry(models.Model):
    STATUS_OPEN = 0
    STATUS_DONE = 1
    STATUS_VALIDATED = 2
    STATUS_EXPIRED = 3
    STATUS_REJECTED = 4

    STATUS_CHOICES = [
        (STATUS_OPEN, _('Open')),
        (STATUS_VALIDATED, _('Validated')),
        (STATUS_EXPIRED, _('Expired')),
        (STATUS_DONE, _('Done')),
        (STATUS_REJECTED, _('Rejected')),
    ]
    created_time = models.DateTimeField(_("created time"), auto_now_add=True, db_index=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    last_check_time = models.DateTimeField(_("last check time"), null=True, blank=True)

    status = models.PositiveSmallIntegerField(_('status'), choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    done_time = models.DateTimeField(_('done time'), null=True, blank=True)
    validated_time = models.DateTimeField(_("validated time"), null=True, blank=True)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='user_inquiries')
    user_page = models.ForeignKey(UserPage, on_delete=models.CASCADE)

    class Meta:
        db_table = "insta_inquiries"
        verbose_name_plural = _('user inquiries')
        unique_together = ('order', 'user_page')


class CoinTransaction(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    user = models.ForeignKey('accounts.User', related_name='coin_transactions', on_delete=models.CASCADE)
    amount = models.IntegerField(_('amount'))
    description = models.TextField(_("action"), blank=True)
    inquiry = models.ForeignKey(UserInquiry, on_delete=models.PROTECT, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        db_table = "insta_transactions"

    def __str__(self):
        return f"{self.user} - {self.amount}"

    def clean(self):
        if not self.inquiry and not self.order:
            ValidationError(_("both inquiry and order can not be None."))


class RoutedDjongoManager(djongo_models.DjongoManager):
    def __init__(self):
        super().__init__()
        self._db = 'mongo'


class BaseInstaEntity(djongo_models.Model):
    created_time = djongo_models.DateTimeField(auto_now_add=True)
    media_url = djongo_models.CharField(max_length=150)
    media_id = djongo_models.BigIntegerField()
    action = djongo_models.CharField(max_length=10, choices=InstaAction.ACTION_CHOICES)
    username = djongo_models.CharField(max_length=100)
    user_id = djongo_models.BigIntegerField()
    comment = djongo_models.TextField(null=True)
    comment_id = djongo_models.BigIntegerField(null=True)
    comment_time = djongo_models.DateTimeField(null=True)
    follow_time = djongo_models.DateTimeField(null=True)

    objects = RoutedDjongoManager()

    class Meta:
        managed = False
        unique_together = ('media_id', 'user_id', 'action')

    @classmethod
    def _get_table_model(cls, action, page_id, create=True):
        table_name = ""
        model_name = ""
        if action == InstaAction.ACTION_LIKE or action == InstaAction.ACTION_COMMENT:
            table_name = f"post_{page_id}"
            model_name = f"Post{page_id}"
        elif action == InstaAction.ACTION_FOLLOW:
            table_name = f"page_{page_id}"
            model_name = f"Page{page_id}"
        app_models = cls._meta.apps.all_models[cls._meta.app_label]
        if model_name not in app_models:
            model = type(model_name, (cls,), {'__module__': cls.__module__})
            model._meta.db_table = table_name
            if create:
                all_tables = connection.introspection.table_names()
                with connection.schema_editor() as schema:
                    try:
                        if model._meta.db_table not in all_tables:
                            schema.create_model(model)
                    except Exception as e:
                        logger.error(f"create table got exception: {e}")
                        return None
        else:
            model = app_models[model_name]
        return model

    @classmethod
    def get_model(cls, action, page_id):
        try:
            model = cls._get_table_model(action, page_id)
        except Exception as e:
            logger.error(f"hash table got exception: {e}")
            return None

        return model

    @classmethod
    def drop_model(cls, action, page_id):
        try:
            model = cls._get_table_model(action, page_id, False)
            all_tables = connection.introspection.table_names()
        except Exception as e:
            logger.error(f"hash table got exception: {e}")
            return False

        with connection.schema_editor() as schema:
            try:
                if model._meta.db_table in all_tables:
                    schema.delete_model(model)
            except Exception as e:
                logger.error(f"create table got exception: {e}")
                return False

        return True
