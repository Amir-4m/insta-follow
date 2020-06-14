import logging

from django.core.cache import cache
from django.core.paginator import Paginator
from django.template import Template, Context
from telegram import ParseMode, InlineKeyboardMarkup

from apps.instagram_app.models import InstaPage, UserPage, Order, UserInquiry, InstaAction
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
                    bot.send_message(chat_id=update.effective_user.id, text="message could not be sent !")
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
                defaults=dict(
                    instagram_username=instagram_username,
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

        except Exception as e:
            logger.error(f"adding insta page got error {e}")
            bot.send_message(
                text=texts.ERROR_MESSAGE,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )

    @staticmethod
    def get_order_list(bot, update, user, session, counter=1):
        try:
            data = ''
            if update.callback_query:
                data = update.callback_query.data
            try:
                if data == 'next':
                    session['counter'] += 1
                    counter = session.get('counter')
                elif data == 'previous':
                    session['counter'] = session['counter'] - 1
                    counter = session.get('counter')
            except KeyError:
                bot.send_message(
                    text=texts.ERROR_MESSAGE,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
                return
            orders = Order.objects.filter(owner=user)
            p = Paginator(orders, 3)
            page = p.page(counter)
            temp_button = buttons.pagination_button(has_next=page.has_next(), has_previous=page.has_previous())
            if temp_button is not None:
                button = InlineKeyboardMarkup(temp_button)
            else:
                button = None
                if update.callback_query:
                    bot.edit_message_text(
                        text=InstaBotService.render_template(texts.ORDER_LIST, orders=page.object_list),
                        chat_id=update.effective_user.id,
                        reply_markup=button,
                        disable_web_page_preview=True,
                        message_id=update.callback_query.message.message_id,
                        parse_mode=ParseMode.HTML
                    )
                    InstaBotService.refresh_session(bot, update, session)
                    return
            bot.send_message(
                text=InstaBotService.render_template(texts.ORDER_LIST, orders=page.object_list),
                chat_id=update.effective_user.id,
                reply_markup=button,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML

            )
        except Exception as e:
            logger.error(f"getting order list got error {e}")
            bot.send_message(
                text=texts.ORDER_NOT_FOUND,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
        InstaBotService.refresh_session(bot, update, session)

    @staticmethod
    def get_activity_list(bot, update, user, session, counter=1, filter_params=None):
        try:
            data = ''
            inquiries = UserInquiry.objects.select_related(
                'order', 'order__action', 'user_page__page'
            ).filter(
                user_page__user=user
            )
            if filter_params:
                status = [
                    param for param in filter_params if
                    param in [
                        UserInquiry.STATUS_DONE, UserInquiry.STATUS_OPEN, UserInquiry.STATUS_REJECTED,
                        UserInquiry.STATUS_EXPIRED, UserInquiry.STATUS_VALIDATED
                    ]
                ]
                action = [param for param in filter_params if
                          param in [
                              InstaAction.ACTION_COMMENT, InstaAction.ACTION_FOLLOW, InstaAction.ACTION_LIKE
                          ]
                          ]
                if status:
                    inquiries = inquiries.filter(status__in=status)
                if action:
                    inquiries = inquiries.filter(order__action__action_type__in=action)
            if update.callback_query:
                data = update.callback_query.data
            try:
                if data == 'next':
                    session['counter'] += 1
                    counter = session.get('counter')
                elif data == 'previous':
                    session['counter'] = session['counter'] - 1
                    counter = session.get('counter')
            except KeyError:
                bot.send_message(
                    text=texts.ERROR_MESSAGE,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
                return

            p = Paginator(inquiries, 3)
            page = p.page(counter)
            if update.callback_query:
                bot.edit_message_text(
                    text=InstaBotService.render_template(texts.ACTIVITY_LIST, inquiries=page.object_list),
                    chat_id=update.effective_user.id,
                    reply_markup=InlineKeyboardMarkup(
                        buttons.activity(page.has_next(), page.has_previous(), filter_params)),
                    disable_web_page_preview=True,
                    message_id=update.callback_query.message.message_id,
                    parse_mode=ParseMode.HTML

                )
                return
            bot.send_message(
                text=InstaBotService.render_template(texts.ACTIVITY_LIST, inquiries=page.object_list),
                chat_id=update.effective_user.id,
                reply_markup=InlineKeyboardMarkup(
                    buttons.activity(page.has_next(), page.has_previous(), filter_params)),
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
            InstaBotService.refresh_session(bot, update, session)

        except Exception as e:
            logger.error(f"getting activity got error {e}")
            bot.send_message(
                text=texts.ERROR_MESSAGE,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
