import logging

from django.core.cache import cache
from django.core.paginator import Paginator
from django.template import Template, Context

from apps.instagram_app.models import InstaPage, UserPage, Order
from apps.instagram_app.services import InstagramAppService
from apps.telegram_app.models import TelegramUser
from bot import texts, buttons

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
                    username='t-' + str(user_info.id),
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

    @staticmethod
    def render_template(template, **kwargs):
        t = Template(template)
        c = Context(dict(kwargs))
        return t.render(c)

    @staticmethod
    def add_insta_page(bot, update, user, instagram_username):
        try:
            page_info = InstagramAppService.get_page_info(instagram_username, full_info=True)
            page, i_created = InstaPage.objects.get_or_create(
                instagram_user_id=page_info[0],
                instagram_username=instagram_username,
                defaults=dict(
                    followers=page_info[2],
                    following=page_info[3],
                    post_no=page_info[4]
                )

            )

            user_page, u_created = UserPage.objects.get_or_create(user=user, page=page)

            if not u_created and user_page.is_active is False:
                user_page.is_active = True
                user_page.save()

            bot.send_message(
                text=InstaBotService.render_template(
                    texts.PAGE_CREATED,
                    page=user_page.page

                ),
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )

        except Exception:
            bot.send_message(
                text=texts.ERROR_MESSAGE,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )

    @staticmethod
    def get_order_list(bot, update, user, counter=1):
        try:
            orders = Order.objects.filter(owner=user)
            p = Paginator(orders, 2)
            page = p.page(counter)

            bot.send_message(
                text=InstaBotService.render_template(texts.ORDER_LIST, orders=page.object_list),
                chat_id=update.effective_user.id,
                reply_markup=buttons.pagination_button(has_next=page.has_next(), has_previous=page.has_previous())
            )
        except Exception:
            bot.send_message(
                text=texts.ORDER_NOT_FOUND,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )

    @staticmethod
    def paginate_data(bot, update, session, user, data, list_type):
        if data == 'next':
            try:
                session['counter'] += 1
                counter = session.get('counter')
                if list_type == 'order_list':
                    InstaBotService.get_order_list(bot, update, user, counter=counter)
                InstaBotService.refresh_session(bot, update, session)
            except KeyError:
                bot.send_message(
                    text=texts.ERROR_MESSAGE,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
                return

        elif data == 'previous':
            try:
                session['counter'] = session['counter'] - 1
                counter = session.get('counter')
                if list_type == 'order_list':
                    InstaBotService.get_order_list(bot, update, user, counter=counter)
                InstaBotService.refresh_session(bot, update, session)
            except KeyError:
                bot.send_message(
                    text=texts.ERROR_MESSAGE,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
                return
