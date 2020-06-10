import json
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from apps.instagram_app.models import UserInquiry, InstaAction
from bot import texts


def start():
    buttons = [
        [KeyboardButton(texts.CHOICE_PROFILE)],
        [KeyboardButton(texts.CHOICE_CREATE_ORDER)],
        [KeyboardButton(texts.CHOICE_GET_ORDERS)],
        [KeyboardButton(texts.CHOICE_ACTIVITY)],
        [KeyboardButton(texts.CHOICE_ADD_PAGE)],
        [KeyboardButton(texts.CHOICE_DELETE_PAGE)],
        [KeyboardButton(texts.CHOICE_COLLECT_COIN)]
    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def collect_coin_type():
    buttons = [
        [KeyboardButton(texts.CHOICE_BY_LIKE)],
        [KeyboardButton(texts.CHOICE_BY_COMMENT)],
        [KeyboardButton(texts.CHOICE_BY_FOLLOW)],

    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def collect_coin_page(user):
    buttons = [
        [KeyboardButton(user_page.page.instagram_username)] for user_page in user.user_pages.filter(is_active=True)
    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def inquiry(user_page, chosen=None):
    if chosen is None:
        chosen = []
    buttons = []
    temp = []
    for _, btn in enumerate(UserInquiry.objects.filter(user_page=user_page, status=UserInquiry.STATUS_OPEN)):
        if btn.id in chosen:
            temp.append(InlineKeyboardButton(text="✅" + str(btn.id), callback_data=btn.id))
        else:
            temp.append(InlineKeyboardButton(text=btn.id, callback_data=btn.id))
    if len(temp) != 0:
        buttons.append(temp)

    return InlineKeyboardMarkup(buttons)


def order_action():
    buttons = [
        [KeyboardButton(texts.LIKE)],
        [KeyboardButton(texts.COMMENT)],
        [KeyboardButton(texts.FOLLOW)]

    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def order_check():
    buttons = [
        [InlineKeyboardButton(texts.SUBMIT_ORDER, callback_data="submit_order")],
        [InlineKeyboardButton(texts.CANCEL, callback_data="cancel")],
    ]

    return InlineKeyboardMarkup(buttons)


def pagination_button(has_next, has_previous):
    pagination = {
        'prev': [
            [InlineKeyboardButton("صفحه قبلی ⬅", callback_data="previous")],
        ],
        'next': [
            [InlineKeyboardButton("➡ صفحه بعدی", callback_data="next")],

        ]
    }

    if has_next and not has_previous:
        return InlineKeyboardMarkup(pagination['next'])
    elif has_previous and not has_next:
        return InlineKeyboardMarkup(pagination['prev'])
    elif has_next and has_previous:
        return InlineKeyboardMarkup(pagination['next'] + pagination['prev'])
    else:
        return None


def activity(chosen=None):

    if chosen is None:
        chosen = []

    choose_list = [
        (texts.FILTER_OPEN, UserInquiry.STATUS_OPEN),
        (texts.FILTER_VALIDATED, UserInquiry.STATUS_VALIDATED),
        (texts.FILTER_EXPIRED, UserInquiry.STATUS_EXPIRED),
        (texts.FILTER_REJECTED, UserInquiry.STATUS_REJECTED),
        (texts.FILTER_DONE, UserInquiry.STATUS_DONE),
        (texts.FILTER_LIKE, InstaAction.ACTION_LIKE),
        (texts.FILTER_FOLLOW, InstaAction.ACTION_FOLLOW),
        (texts.FILTER_COMMENT, InstaAction.ACTION_COMMENT),
        # (texts.FILTER_BY_PAGE, {'user_page': UserInquiry.STATUS_EXPIRED}),

    ]

    temp = []
    for choice in choose_list:
        if choice[1] in chosen:
            temp.append([InlineKeyboardButton(text="✅" + choice[0], callback_data=choice[1])])
        else:
            temp.append([InlineKeyboardButton(text=choice[0], callback_data=choice[1])])
    return InlineKeyboardMarkup(temp)


def done_inquiry():
    buttons = [
        [InlineKeyboardButton(texts.DONE_INQUIRY, callback_data="done_inquiry")],
        [InlineKeyboardButton(texts.CANCEL, callback_data="cancel")],
    ]

    return InlineKeyboardMarkup(buttons)