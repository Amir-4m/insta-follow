from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


class Action(models.TextChoices):
    LIKE = 'L', _('Like')
    FOLLOW = 'F', _('Follow')
    COMMENT = 'C', _('Comment')

    class Meta:
        db_table = "instagram_action"


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
    instagram_username = models.CharField(_("instagram username"), max_length=50, unique=True)
    instagram_user_id = models.BigIntegerField(_("instagram id"), unique=True)
    followers = models.IntegerField(_("page followers"))
    following = models.IntegerField(_("page following"))
    post_no = models.IntegerField(_("posts number"))
    is_banned = models.BooleanField(_("is baned"), default=False)

    category = models.ManyToManyField(Category)
    owner = models.ManyToManyField("telegram_app.TelegramUser", related_name="insta_pages", through='UserPage')

    class Meta:
        db_table = "instagram_pages"

    def __str__(self):
        return self.instagram_username


class UserPage(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey("telegram_app.TelegramUser", on_delete=models.CASCADE)
    page = models.ForeignKey(InstaPage, on_delete=models.CASCADE)

    class Meta:
        db_table = "instagram_user_pages"

    def __str__(self):
        return f"{self.user.username} with instagram page {self.page.instagram_username}"


class Package(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    slug = models.SlugField(_("slug"), unique=True)
    name = models.CharField(_("package name"), max_length=100)
    follow_target_no = models.IntegerField(_("follow target"))
    like_comment_target_no = models.IntegerField(_("like and comment target"))
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


class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    action_type = models.CharField(_('action type'), choices=Action.choices)
    link = models.URLField(_("link"))
    user_package = models.ForeignKey(UserPackage, on_delete=models.CASCADE)
    target_no = models.IntegerField(_("target like, comment or follower"), blank=True)
    achieved_no = models.IntegerField(_("achieved like, comment or follower"), default=0)
    description = models.TextField(_("description"), blank=True, default='')
    is_enable = models.BooleanField(_("is enable"), default=True)

    class Meta:
        db_table = "instagram_order"

    @property
    def package_target(self):
        if self.action_type == Action.FOLLOW:
            return self.user_package.package.follow_target_no
        elif self.action_type == Action.COMMENT or self.action_type == Action.LIKE:
            return self.user_package.package.like_comment_target_no

    def clean(self):
        if self.target_no >= self.package_target:
            raise ValidationError(_("order target number should not be higher than your package target number !"))
        return super(Order, self).clean()


def __str__(self):
    return f"{self.id} - {self.action_type} for {self.user_package.user_page}"


class UserAssignment(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user_page = models.ForeignKey(UserPage, on_delete=models.CASCADE)
    validated_time = models.DateTimeField(_("validated time"), null=True)
    last_check_time = models.DateTimeField(_("last check time"), null=True)
    check_type = models.CharField(_("type to check"), choices=Action.choices, db_index=True)


class CoinTransaction(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    user = models.ForeignKey('telegram_app.User', related_name='coin_transactions', on_delete=models.CASCADE)
    action = models.CharField(_("action"), max_length=120, blank=True)
    amount = models.IntegerField(_('coin amount'), null=False, blank=False, default=0)

    class Meta:
        db_table = "instagram_coin_transaction"

    def __str__(self):
        return f"{self.user} - {self.amount}"
