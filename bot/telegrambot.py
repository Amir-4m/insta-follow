import logging

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.template import Template, Context
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode
from apps.instagram_app.models import UserPage, InstaPage, InstaAction, Order, UserInquiry, CoinTransaction
from apps.instagram_app.services import InstagramAppService
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

    """
    Creating user page on first login if user has no active page
    """
    if text.startswith('@') and not UserPage.objects.filter(user=user, is_active=True).exists():
        page_id = text.lstrip('@')
        InstaBotService.add_insta_page(bot, update, user, page_id)

    """
    Shows user profile such as telegram username, coin balance, insta pages
    """
    if text == texts.CHOICE_PROFILE:
        user_pages = UserPage.objects.filter(user=user, is_active=True)

        bot.send_message(
            text=InstaBotService.render_template(
                texts.GET_PROFILE,
                user_pages=user_pages,
                user=user,
                coin=user.coin_transactions.all().aggregate(wallet=Sum('amount')).get('wallet', 0)
            ),
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )

    """
    Add the page with the given instagram username to user pages
    """
    if text == texts.CHOICE_ADD_PAGE:
        session['state'] = 'add_page'

        bot.send_message(
            text=texts.ENTER_PAGE_USERNAME,
            chat_id=update.effective_user.id,
        )

    """
    Remove the page with the given id from user active pages
    """
    if text == texts.CHOICE_DELETE_PAGE:
        session['state'] = 'delete_page'
        user_pages = UserPage.objects.filter(user=user, is_active=True)

        bot.send_message(
            text=InstaBotService.render_template(texts.PAGE_LIST, user_pages=user_pages),
            chat_id=update.effective_user.id,
        )

    """
    Shows a list of inquiries that user must do with the chosen action
    """
    if text == texts.CHOICE_COLLECT_COIN:
        session['state'] = 'collect_coin'
        bot.send_message(
            text=texts.COLLECT_COIN_TYPES,
            chat_id=update.effective_user.id,
            reply_markup=buttons.collect_coin_type()
        )

    """
    Shows a list of user orders
    """
    if text == texts.CHOICE_GET_ORDERS:
        session['counter'] = 1
        session['list_type'] = 'order_list'

        InstaBotService.get_order_list(bot, update, user)

    if text == texts.CHOICE_CREATE_ORDER:
        session['state'] = 'create_order_action'
        bot.send_message(
            text=texts.ORDER_CREATE_ACTION,
            chat_id=update.effective_user.id,
            reply_markup=buttons.order_action()
        )

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
        except UserPage.DoesNotExist:
            bot.send_message(
                text=texts.PAGE_NOT_FOUND,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
    else:
        bot.send_message(
            text=texts.ERROR_MESSAGE,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )


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
    except UserPage.DoesNotExist:
        bot.send_message(
            text=texts.PAGE_NOT_FOUND,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
        return

    valid_orders = Order.objects.filter(is_enable=True, action=action).order_by('-id')

    valid_inquiries = []
    given_entities = []
    for order in valid_orders:
        if order.entity_id in given_entities:
            continue
        user_inquiry, _c = UserInquiry.objects.get_or_create(order=order, defaults=dict(user_page=user_page))
        if user_inquiry and user_inquiry.status == UserInquiry.STATUS_OPEN:
            valid_inquiries.append(user_inquiry)
            given_entities.append(order.entity_id)
    session['inquiry_ids'] = [inquiry.id for inquiry in valid_inquiries[:10]]
    bot.send_message(
        text=InstaBotService.render_template(texts.INQUIRY_LIST, inquiries=valid_inquiries[:10]),
        chat_id=update.effective_user.id,
        reply_markup=buttons.inquiry(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def check_inquiry(bot, update, session=None):
    text = update.message.text
    if text == texts.BACK:
        session['state'] = 'collect_coin'
        bot.send_message(
            text=texts.COLLECT_COIN_TYPES,
            chat_id=update.effective_user.id,
            reply_markup=buttons.collect_coin_type()
        )
    elif text == texts.DONE_INQUIRY:
        done_ids = session.get('inquiry_ids')
        page_id = session.get('active_page')
        InstagramAppService.check_user_action(done_ids, page_id)
        bot.send_message(
            text=texts.CHECK_INQUIRY,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )

    session.pop('inquiry_ids')
    session.pop('active_page')
    session.pop('action')

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
    target = update.message.text
    session['order_target'] = target
    session['state'] = 'order_create_final'
    user = session.get('user')
    link = session.get('order_link')
    order_action = session.get('order_action')
    price = target * order_action.buy_value
    bot.send_message(
        text=InstaBotService.render_template(
            texts.ORDER_CREATE_CHECK,
            order_action=order_action,
            link=link,
            target=target,
            price=price,
            username=user.username
        ),
        chat_id=update.effective_user.id,
        reply_markup=buttons.order_check()
    )

    InstaBotService.refresh_session(bot, update, session)


@run_async
@add_session()
def order_create_final(bot, update, session=None):
    data = update.callback_query.data
    user = session.get('user')
    link = session.get('order_link')
    order_action = session.get('order_action')
    target = session.get('target')

    if data == texts.SUBMIT_ORDER:
        with transaction.atomic():
            user = TelegramUser.objects.select_for_update().get(id=user.id)
            if user.coin_transactions.all().aggregate(
                    wallet=Coalesce(Sum('amount'), 0)
            )['wallet'] < order_action.buy_value * target:
                bot.send_message(
                    text=texts.NOT_ENOUGH_COIN,
                    chat_id=update.effective_user.id,
                )
                return

            ct = CoinTransaction.objects.create(user=user, amount=-(order_action.buy_value * target))
            order = Order.objects.create(
                action=order_action,
                link=link,
                target_no=target,
                owner=user,
            )
            ct.order = order
            ct.description = f"create order {order.id}"
            ct.save()

        bot.send_message(
            text=texts.ORDER_CREATE_FINAL,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()

        )
    elif data == texts.CANCEL:
        bot.send_message(
            text=texts.ORDER_CANCEL,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
    session.pop('order_link')
    session.pop('order_action')
    session.pop('target')
    InstaBotService.refresh_session(bot, update, session)
