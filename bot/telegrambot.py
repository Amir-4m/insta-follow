import logging
import json
import re

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode
from apps.instagram_app.models import UserPage, InstaAction, Order, CoinTransaction, UserInquiry
from apps.instagram_app.services import CustomService
from apps.telegram_app.models import TelegramUser
from .decorators import add_session
from . import texts, buttons
from .services import InstaBotService

logger = logging.getLogger(__name__)


@run_async
@add_session(clear=True)
def start(bot, update, session):
    user = session.get("user")
    if UserPage.objects.filter(user=user, is_active=True).exists():
        bot.send_message(
            chat_id=update.effective_user.id,
            text=texts.START_USER_HAS_PAGE.format(user.first_name),
            reply_markup=buttons.start()
        )
    else:
        bot.send_message(
            chat_id=update.effective_user.id,
            text=texts.START_USER_HAS_NO_PAGE.format(user.first_name),
        )


@run_async
@add_session(clear=True)
def stop(bot, update, session):
    pass


@run_async
@add_session()
def dispatcher(bot, update, session):
    user = session.get('user')
    text = update.message.text
    print(session)
    if text.startswith('@') and not UserPage.objects.filter(user=user, is_active=True).exists():

        """
        Creating user page on first login if user has no active page
        """

        page_id = text.lstrip('@')
        InstaBotService.add_insta_page(bot, update, user, page_id)
        return

    elif text == texts.CHOICE_PROFILE:

        """
        Shows user profile such as telegram username, coin balance, insta pages
        """

        user_pages = UserPage.objects.filter(user=user, is_active=True)

        bot.send_message(
            text=InstaBotService.render_template(
                texts.GET_PROFILE,
                user_pages=user_pages,
                user=user,
                coin=user.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet', 0) or 0
            ),
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return

    elif text == texts.CHOICE_ADD_PAGE:

        """
        Add the page with the given instagram username to user pages
        """

        session['state'] = 'add_page'

        bot.send_message(
            text=texts.ENTER_PAGE_USERNAME,
            chat_id=update.effective_user.id,
        )

    elif text == texts.CHOICE_DELETE_PAGE:
        """
        Remove the page with the given id from user active pages
        """

        session['state'] = 'delete_page'
        user_pages = UserPage.objects.filter(user=user, is_active=True)

        bot.send_message(
            text=InstaBotService.render_template(texts.PAGE_LIST, user_pages=user_pages),
            chat_id=update.effective_user.id,
        )

    elif text == texts.CHOICE_COLLECT_COIN:
        """
        Shows a list of inquiries that user must do with the chosen action
        """

        session['state'] = 'collect_coin'
        bot.send_message(
            text=texts.COLLECT_COIN_TYPES,
            chat_id=update.effective_user.id,
            reply_markup=buttons.collect_coin_type()
        )

    elif text == texts.CHOICE_GET_ORDERS:
        """
        Shows a list of user orders
        """
        session['counter'] = 1
        session['list_type'] = 'order_list'

        InstaBotService.get_order_list(bot, update, user)
        InstaBotService.refresh_session(bot, update, session)
        return

    elif text == texts.CHOICE_CREATE_ORDER:
        session['state'] = 'create_order_action'
        bot.send_message(
            text=texts.ORDER_CREATE_ACTION,
            chat_id=update.effective_user.id,
            reply_markup=buttons.order_action()
        )
    elif text == texts.CHOICE_ACTIVITY:
        session['state'] = 'get_activity'
        session['counter'] = 1
        InstaBotService.get_activity_list(bot, update, user)
        InstaBotService.refresh_session(bot, update, session)

    else:
        call_state_function(bot, update)
        return

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def call_state_function(bot, update, session):
    user = session.get('user')
    if update.callback_query:
        data = update.callback_query.data
        list_type = session.get('list_type')
        if list_type:
            return InstaBotService.paginate_data(bot, update, session, user, data, list_type)

    state = session.get('state')
    try:
        eval(state)(bot, update)
    except Exception:
        session.pop('state', None)
        bot.send_message(chat_id=update.effective_user.id,
                         text=texts.WRONG_COMMAND,
                         reply_markup=buttons.start())


@run_async
@add_session()
def add_page(bot, update, session=None):
    text = update.message.text
    user = session.get('user')
    InstaBotService.add_insta_page(bot, update, user, text)
    return


@run_async
@add_session()
def delete_page(bot, update, session=None):
    text = update.message.text
    user = session.get('user')

    if text.startswith('/'):
        try:
            page_id = text.lstrip('/')
            user_page = UserPage.objects.select_related('page').get(user=user, id=page_id)
            user_page.is_active = False
            user_page.save()

            bot.send_message(
                text=texts.PAGE_DELETED.format(user_page.page.instagram_username),
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
            return
        except UserPage.DoesNotExist as e:
            logger.error(f"TLG-error occurred in getting insta page: {e}")
            bot.send_message(
                text=texts.PAGE_NOT_FOUND,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
            return
    else:
        bot.send_message(
            text=texts.ERROR_MESSAGE,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return


@run_async
@add_session()
def collect_coin(bot, update, session=None):
    text = update.message.text
    user = session.get('user')
    session['state'] = 'get_inquiry'

    if text == texts.CHOICE_BY_LIKE:
        session['action'] = InstaAction.ACTION_LIKE

    elif text == texts.CHOICE_BY_COMMENT:
        session['action'] = InstaAction.ACTION_COMMENT

    elif text == texts.CHOICE_BY_FOLLOW:
        session['action'] = InstaAction.ACTION_FOLLOW

    else:
        bot.send_message(chat_id=update.effective_user.id,
                         text=texts.WRONG_COMMAND,
                         reply_markup=buttons.start())
        return

    bot.send_message(
        text=texts.COLLECT_COIN_PAGE,
        chat_id=update.effective_user.id,
        reply_markup=buttons.collect_coin_page(user)
    )

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def get_inquiry(bot, update, session=None):
    page_username = update.message.text
    action = session.get('action')
    user = session.get('user')
    session['state'] = 'check_inquiry'
    try:
        user_page = UserPage.objects.get(page__instagram_username=page_username, user=user, is_active=True)
        session['active_page'] = user_page.id

    except UserPage.DoesNotExist as e:
        logger.error(f"TLG-error occurred in getting user page of inquiry: {e}")
        bot.send_message(
            text=texts.PAGE_NOT_FOUND,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return

    try:
        inquiries = CustomService.get_or_create_inquiries(user_page, action, limit=10)
        if len(inquiries) >= 1:
            session['inquiry_ids'] = [inquiry.id for inquiry in inquiries]
            bot.send_message(
                text=InstaBotService.render_template(texts.INQUIRY_LIST, inquiries=inquiries),
                chat_id=update.effective_user.id,
                reply_markup=buttons.inquiry(user_page=user_page),
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        else:
            bot.send_message(
                text=texts.INQUIRY_NOT_FOUND,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start(),
            )

    except Exception as e:
        logger.error(f"TLG-error occurred in getting inquiry: {e}")
        bot.send_message(
            text=texts.ERROR_MESSAGE,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def check_inquiry(bot, update, session=None):
    inquiry_ids = session.get('inquiry_ids')
    if "done_ids" not in session:
        session['done_ids'] = []
    page_id = session.get('active_page')
    if update.callback_query:
        data = update.callback_query.data
        if data != 'submit_inquiry':
            data = int(data)
            if data not in session['done_ids']:
                session['done_ids'].append(data)

            else:
                session['done_ids'].remove(data)
            inquiries = UserInquiry.objects.filter(id__in=inquiry_ids, status=UserInquiry.STATUS_OPEN)

            bot.edit_message_text(
                text=InstaBotService.render_template(texts.INQUIRY_LIST, inquiries=inquiries),
                chat_id=update.effective_user.id,
                reply_markup=buttons.inquiry(user_page=page_id, chosen=session['done_ids']),
                disable_web_page_preview=True,
                message_id=update.callback_query.message.message_id,
                parse_mode=ParseMode.HTML

            )
            InstaBotService.refresh_session(bot, update, session)

        else:
            try:

                UserInquiry.objects.filter(
                    id__in=session['done_ids'], user_page=page_id, status=UserInquiry.STATUS_OPEN
                ).update(status=UserInquiry.STATUS_DONE)

                bot.edit_message_text(
                    text=texts.CHECK_INQUIRY,
                    chat_id=update.effective_user.id,
                    message_id=update.callback_query.message.message_id,
                )
                bot.send_message(
                    text=texts.BACK_TO_MENU,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
            except Exception as e:
                logger.error(f"TLG-error occurred in checking inquiry: {e}")
                bot.send_message(
                    text=texts.ERROR_MESSAGE,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
                return

    text = update.message.text
    if text == texts.BACK:
        session['state'] = 'collect_coin'
        bot.send_message(
            text=texts.COLLECT_COIN_TYPES,
            chat_id=update.effective_user.id,
            reply_markup=buttons.collect_coin_type()
        )

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def create_order_action(bot, update, session=None):
    text = update.message.text
    if text == texts.LIKE:
        session['order_action'] = InstaAction.ACTION_LIKE
    elif text == texts.COMMENT:
        session['order_action'] = InstaAction.ACTION_COMMENT
    elif text == texts.FOLLOW:
        session['order_action'] = InstaAction.ACTION_FOLLOW

    if session['order_action'] in [InstaAction.ACTION_LIKE, InstaAction.ACTION_COMMENT]:
        bot_text = texts.ORDER_CREATE_LINK_LC
    else:
        bot_text = texts.ORDER_CREATE_LINK_F

    session['state'] = 'create_order_link'

    bot.send_message(
        text=bot_text,
        chat_id=update.effective_user.id,
    )

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def create_order_link(bot, update, session=None):
    text = update.message.text
    session['order_link'] = text
    session['state'] = 'create_order_check'

    bot.send_message(
        text=texts.ORDER_CREATE_TARGET,
        chat_id=update.effective_user.id,
    )

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def create_order_check(bot, update, session=None):
    try:
        target = int(update.message.text)
        session['order_target'] = target
        session['state'] = 'order_create_final'
        user = session.get('user')
        link = session.get('order_link')
        order_action = session.get('order_action')
        insta_action = InstaAction.objects.get(action_type=order_action)
        price = target * insta_action.buy_value
        bot.send_message(
            text=InstaBotService.render_template(
                texts.ORDER_CREATE_CHECK,
                order_action=insta_action.get_action_type_display(),
                link=link,
                target=target,
                price=price,
                username=user.first_name
            ),
            chat_id=update.effective_user.id,
            reply_markup=buttons.order_check()
        )

    except Exception as e:
        logger.error(f"TLG-error occurred in check section of create order: {e}")
        bot.send_message(
            text=texts.ERROR_MESSAGE,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return
    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def order_create_final(bot, update, session=None):
    try:
        data = update.callback_query.data
        user = session.get('user')
        link = session.get('order_link')
        order_action = session.get('order_action')
        insta_action = InstaAction.objects.get(action_type=order_action)
        target = int(session.get('order_target'))
        if data == 'submit_order':
            with transaction.atomic():
                user = TelegramUser.objects.select_for_update().get(id=user.id)
                if user.coin_transactions.all().aggregate(
                        wallet=Coalesce(Sum('amount'), 0)
                )['wallet'] < insta_action.buy_value * target:
                    bot.send_message(
                        text=texts.NOT_ENOUGH_COIN,
                        chat_id=update.effective_user.id,
                        reply_markup=buttons.start()

                    )
                    session.pop('order_link')
                    session.pop('order_action')
                    session.pop('order_target')
                    InstaBotService.refresh_session(bot, update, session)
                    return
                ct = CoinTransaction.objects.create(user=user, amount=-(insta_action.buy_value * target))
                order = Order.objects.create(
                    action=insta_action,
                    link=link,
                    target_no=target,
                    owner=user,
                )
                ct.order = order
                ct.description = f"create order {order.id}"
                ct.save()

            bot.edit_message_text(
                text=texts.ORDER_CREATE_FINAL,
                chat_id=update.effective_user.id,
                message_id=update.callback_query.message.message_id,

            )

            bot.send_message(
                text=texts.BACK_TO_MENU,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )

        elif data == 'cancel':
            bot.edit_message_text(
                text=texts.ORDER_CANCEL,
                chat_id=update.effective_user.id,
                message_id=update.callback_query.message.message_id,
            )
            bot.send_message(
                text=texts.BACK_TO_MENU,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )

        session.pop('order_link')
        session.pop('order_action')
        session.pop('order_target')

        InstaBotService.refresh_session(bot, update, session)
    except Exception as e:

        logger.error(f"TLG-error occurred in final section of create order: {e}")
        bot.edit_message_text(
            text=texts.ERROR_MESSAGE,
            chat_id=update.effective_user.id,
            message_id=update.callback_query.message.message_id,
        )
        bot.send_message(
            text=texts.BACK_TO_MENU,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return


@run_async
@add_session()
def get_activity(bot, update, session=None):
    user = session.get('user')
    statuses = []
    types = []
    if "chosen_filters" not in session:
        session['chosen_filters'] = []
    try:
        if update.callback_query:
            data = update.callback_query.data
            if data is not None and data.isdigit():
                data = int(data)
                statuses.append(data)

            elif data is not None and data.isalpha():
                types.append(data)
            if data not in session['chosen_filters']:
                session['chosen_filters'].append(data)
            else:
                session['chosen_filters'].remove(data)
            InstaBotService.get_activity_list(bot, update, user, session['chosen_filters'])
            InstaBotService.refresh_session(bot, update, session)

        elif update.message.text and re.search(r'[0-9]+', update.message.text):
            inquiry_id = re.findall(r'\d+', update.message.text).pop()
            session['state'] = 'check_single_inquiry'
            session['inquiry'] = inquiry_id
            inq = UserInquiry.objects.get(id=inquiry_id)

            if inq.status != UserInquiry.STATUS_OPEN:
                bot.send_message(
                    text=texts.INQUIRY_NOT_FOUND,
                    chat_id=update.effective_user.id,
                    reply_markup=buttons.start()
                )
                return

            bot.send_message(
                text=InstaBotService.render_template(texts.SINGLE_INQUIRY_SELECT, inquiry=inq),
                chat_id=update.effective_user.id,
                parse_mode=ParseMode.HTML,
                reply_markup=buttons.done_inquiry()
            )

            InstaBotService.refresh_session(bot, update, session)

    except Exception as e:
        logger.error(f"get activity got error {e}")
        bot.send_message(
            text=texts.ERROR_MESSAGE,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )


@run_async
@add_session()
def check_single_inquiry(bot, update, session=None):
    data = update.callback_query.data

    if data == "done_inquiry":
        try:
            inquiry = UserInquiry.objects.get(id=session['inquiry'])
            inquiry.status = UserInquiry.STATUS_DONE
            inquiry.save()
            bot.edit_message_text(
                text=texts.CHECK_INQUIRY,
                chat_id=update.effective_user.id,
                message_id=update.callback_query.message.message_id,
            )
            bot.send_message(
                text=texts.BACK_TO_MENU,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
        except UserInquiry.DoesNotExist:
            bot.send_message(
                text=texts.INQUIRY_NOT_FOUND,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
        except Exception as e:
            logger.error(f"check single inquiry gor error {e}")
            bot.send_message(chat_id=update.effective_user.id,
                             text=texts.WRONG_COMMAND,
                             reply_markup=buttons.start())
