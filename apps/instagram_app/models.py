import logging
from hashlib import md5

from django.db import models, connection
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _
from djongo import models as djongo_models

logger = logging.getLogger(__name__)

ACTION_CHOICES = [
    ('L', _('Like')),
    ('F', _('Follow')),
    ('C', _('Comment')),
]


class Category(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    name = models.CharField(_("category name"), max_length=100, unique=True)

    class Meta:
        db_table = "categories"

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
        db_table = "insta_pages"

    def __str__(self):
        return self.instagram_username


class UserPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey("accounts.User", related_name='user_pages', on_delete=models.CASCADE)
    page = models.ForeignKey(InstaPage, related_name='user_pages', on_delete=models.PROTECT)

    class Meta:
        db_table = "insta_user_pages"
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
    coins = models.PositiveIntegerField(_('coins'))
    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        db_table = "insta_packages"

    def __str__(self):
        return f"{self.slug} {self.name}"


class UserPackage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name='user_packages')
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    is_consumed = models.BooleanField(_("totally consumed"), default=False)

    remaining_follow = models.IntegerField(_("follow remaining"), null=True, blank=True)
    remaining_comment = models.IntegerField(_("comment remaining"), null=True, blank=True)
    remaining_like = models.IntegerField(_("like remaining"), null=True, blank=True)

    class Meta:
        db_table = "insta_user_packages"

    def __str__(self):
        return f"{self.user_id} - {self.package.name}"


# Inventory
class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    action_type = models.CharField(_('action type'), max_length=10, choices=ACTION_CHOICES)
    link = models.URLField(_("link"))
    media_url = models.TextField(_("media url"), blank=True)
    user_package = models.ForeignKey(UserPackage, on_delete=models.CASCADE)
    target_no = models.IntegerField(_("target like, comment or follower"), blank=True)
    achieved_no = models.IntegerField(_("achieved like, comment or follower"), default=0)
    description = models.TextField(_("description"), blank=True, default='')
    is_enable = models.BooleanField(_("is enable"), default=True)

    class Meta:
        db_table = "insta_user_orders"

    def __str__(self):
        return f"{self.id} - {self.action_type} for {self.user_package_id}"

    def clean(self):
        if self.target_no and self.target_no > self.package_target:
            raise ValidationError(_("order target number should not be higher than your package target number !"))
        elif self.target_no is None:
            self.target_no = self.package_target

    @property
    def package_target(self):
        if self.action_type == 'F':
            return self.user_package.package.follow_target_no
        elif self.action_type == 'C':
            return self.user_package.package.comment_target_no
        elif self.action_type == 'L':
            return self.user_package.package.like_target_no


class UserInquiry(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user_page = models.ForeignKey(UserPage, on_delete=models.CASCADE)
    validated_time = models.DateTimeField(_("validated time"), null=True, blank=True)
    last_check_time = models.DateTimeField(_("last check time"), null=True, blank=True)

    class Meta:
        db_table = "insta_inquiries"
        unique_together = ('order', 'user_page')


class CoinTransaction(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    user = models.ForeignKey('accounts.User', related_name='coin_transactions', on_delete=models.CASCADE)
    amount = models.IntegerField(_('coin amount'), null=False, blank=False, default=0)
    description = models.TextField(_("action"), blank=True)
    inquiry = models.ForeignKey(UserInquiry, null=True, blank=True, on_delete=models.PROTECT)
    user_package = models.ForeignKey(UserPackage, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = "insta_transactions"

    def __str__(self):
        return f"{self.user} - {self.amount}"

    @property
    def user_balance(self):
        return self.user.coin_transactions.all().aggregate(Sum('amount'))


class BaseInstaEntity(djongo_models.Model):
    created_time = djongo_models.DateTimeField(auto_now_add=True)
    media_url = djongo_models.CharField(max_length=150)
    media_id = djongo_models.BigIntegerField()
    action_type = djongo_models.CharField(max_length=10, choices=ACTION_CHOICES)
    username = djongo_models.CharField(max_length=100)
    user_id = djongo_models.BigIntegerField()
    comment = djongo_models.TextField(null=True)
    comment_id = djongo_models.BigIntegerField(null=True)
    comment_time = djongo_models.DateTimeField(null=True)
    follow_time = djongo_models.DateTimeField(null=True)

    objects = djongo_models.DjongoManager()

    class Meta:
        managed = False
        unique_together = ('media_id', 'user_id', 'action_type')

    @classmethod
    def _get_table_model(cls, action, link, create=True):
        link_hash = md5(link.encode('utf-8')).hexdigest()
        if action == 'L' or action == 'C':
            table_name = f"post_{link_hash}"
            model_name = f"Post{link_hash}"
        elif action == 'F':
            table_name = f"page_{link_hash}"
            model_name = f"Page{link_hash}"
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
    def get_model(cls, action, link):
        try:
            model = cls._get_table_model(action, link)
        except Exception as e:
            logger.error(f"hash table got exception: {e}")
            return None

        return model

    @classmethod
    def drop_model(cls, action, post_link):
        try:
            model = cls._get_table_model(action, post_link, False)
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
