from django.contrib import admin
from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'username', 'first_name', 'is_enable']
    search_fields = ['id', 'user_id', 'username', 'first_name']
    list_filter = ['is_enable']
