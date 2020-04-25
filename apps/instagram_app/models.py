import logging
from hashlib import md5

from django.db import models, connection
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class Action(models.TextChoices):
    LIKE = 'L', _('Like')
    FOLLOW = 'F', _('Follow')
    COMMENT = 'C', _('Comment')


class Category(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    name = models.CharField(_("category name"), max_length=100, unique=True)

    class Meta:
        db_table = "instagram_category"

    def __str__(self):
        return f"{self.name}"


class InstaPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    instagram_username = models.CharField(_("instagram username"), max_length=50)
    instagram_user_id = models.BigIntegerField(_("instagram id"), unique=True)
    followers = models.IntegerField(_("page followers"))
    following = models.IntegerField(_("page following"))
    post_no = models.IntegerField(_("posts number"))
    is_banned = models.BooleanField(_("is banned"), default=False)

    category = models.ManyToManyField(Category)
    owner = models.ManyToManyField("accounts.User", through='UserPage', related_name='insta_pages')

    class Meta:
        db_table = "instagram_pages"

    def __str__(self):
        return self.instagram_username


class UserPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey("accounts.User", related_name='user_pages', on_delete=models.CASCADE)
    page = models.ForeignKey(InstaPage, related_name='user_pages', on_delete=models.PROTECT)

    class Meta:
        db_table = "instagram_user_pages"
        unique_together = ['user', 'page']

    def __str__(self):
        return f"{self.user.username} with instagram page {self.page.instagram_username}"


class Package(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    slug = models.SlugField(_("slug"), unique=True)
    name = models.CharField(_("package name"), max_length=100)
    follow_target_no = models.IntegerField(_("follow target"))
    like_target_no = models.IntegerField(_("like target"))
    comment_target_no = models.IntegerField(_("comment target"))
    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        db_table = "instagram_package"

    def __str__(self):
        return f"{self.slug} {self.name}"


class UserPackage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    user_page = models.ForeignKey(UserPage, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)

    class Meta:
        db_table = "instagram_user_package"

    def __str__(self):
        return f"{self.user_page.id} - {self.package.name}"


# Inventory
class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    action_type = models.CharField(_('action type'), max_length=10, choices=Action.choices)
    link = models.URLField(_("link"))
    user_package = models.ForeignKey(UserPackage, on_delete=models.CASCADE)
    target_no = models.IntegerField(_("target like, comment or follower"), blank=True)
    achieved_no = models.IntegerField(_("achieved like, comment or follower"), default=0)
    description = models.TextField(_("description"), blank=True, default='')
    is_enable = models.BooleanField(_("is enable"), default=True)

    class Meta:
        db_table = "instagram_order"

    def __str__(self):
        return f"{self.id} - {self.action_type} for {self.user_package.user_page}"

    def clean(self):
        if self.target_no >= self.package_target:
            raise ValidationError(_("order target number should not be higher than your package target number !"))

    @property
    def package_target(self):
        if self.action_type == Action.FOLLOW:
            return self.user_package.package.follow_target_no
        elif self.action_type == Action.COMMENT:
            return self.user_package.package.comment_target_no
        elif self.action_type == Action.LIKE:
            return self.user_package.package.like_target_no


class UserAssignment(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user_page = models.ForeignKey(UserPage, on_delete=models.CASCADE)
    validated_time = models.DateTimeField(_("validated time"), null=True)
    last_check_time = models.DateTimeField(_("last check time"), null=True)
    check_type = models.CharField(_("type to check"), max_length=10, choices=Action.choices, db_index=True)

    class Meta:
        db_table = "instagram_user_assignment"

    def __str__(self):
        # TODO: will change
        return f"{self.user_page_id} action: {self.check_type}"


class CoinTransaction(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    user = models.ForeignKey('telegram_app.TelegramUser', related_name='coin_transactions', on_delete=models.CASCADE)
    action = models.CharField(_("action"), max_length=120, blank=True)
    amount = models.IntegerField(_('coin amount'), null=False, blank=False, default=0)

    class Meta:
        db_table = "instagram_coin_transaction"

    def __str__(self):
        return f"{self.user} - {self.amount}"


class BaseInstaEntity(models.Model):
    created_time = models.DateTimeField(auto_now_add=True)
    media_url = models.CharField(max_length=150)
    media_id = models.BigIntegerField()
    action_type = models.CharField(max_length=10, choices=Action.choices)
    username = models.CharField(max_length=100)
    user_id = models.BigIntegerField()
    comment = models.TextField(null=True)
    comment_id = models.BigIntegerField(null=True)
    comment_time = models.DateTimeField(null=True)
    follow_time = models.DateTimeField(null=True)

    # TODO: add follow needed fields

    class Meta:
        managed = False
        abstract = True
        unique_together = ('media_id', 'user_id', 'action_type')

    @classmethod
    def _get_table_model(cls, target_link, create=True):
        table_name_hash = md5(target_link.encode('utf-8')).hexdigest()
        table_name = f"entity_{table_name_hash}"
        model_name = f"Entity{table_name_hash}"
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
    def get_model(cls, post_link):
        try:
            model = cls._get_table_model(post_link)
        except Exception as e:
            logger.error(f"hash table got exception: {e}")
            return None

        return model

    @classmethod
    def drop_model(cls, post_link):
        try:
            model = cls._get_table_model(post_link, False)
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
