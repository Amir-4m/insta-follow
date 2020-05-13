import logging

from django.core.cache import cache

from apps.telegram_app.models import TelegramUser

logger = logging.getLogger(__name__)


class InstaBotService(object):

    @staticmethod
    def refresh_session(bot, update, session=None, clear=False):
        user_info = update.effective_user
        ck = f'telegram_user_session_{user_info.id}'

        if clear:
            cache.delete(ck)

        if session:
            cache.set(ck, session)
            return session

        if not cache.get(ck):

            try:
                user, _c = TelegramUser.objects.get_or_create(
                    telegram_user_id=user_info.id,
                    username=user_info.username,
                    defaults=dict(
                        first_name=user_info.first_name or '',
                    )
                )

            except Exception as e:

                logger.error(f"create bot user: {user_info.id} got exception: {e}")
            else:
                if not user.is_enable:
                    bot.send_message(update.effective_user.id, "message could not be sent !")
                    return
                cache.set(ck, {'user': user}, 300)
        return cache.get(ck)
