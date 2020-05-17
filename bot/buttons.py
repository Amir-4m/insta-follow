from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from bot import texts


def start():
    buttons = [
        [KeyboardButton(texts.CHOICE_PROFILE)],
        [KeyboardButton(texts.CHOICE_CREATE_ORDER)],
        [KeyboardButton(texts.CHOICE_GET_ORDERS)],
        [KeyboardButton(texts.CHOICE_ADD_PAGE)],
        [KeyboardButton(texts.CHOICE_DELETE_PAGE)],
        [KeyboardButton(texts.CHOICE_COLLECT_COIN)]
    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def collect_coin_type():
    buttons = [
        [KeyboardButton(texts.CHOICE_BY_LIKE),
         KeyboardButton(texts.CHOICE_BY_COMMENT),
         KeyboardButton(texts.CHOICE_BY_FOLLOW)
         ],

    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def collect_coin_page(user):
    buttons = [
        [KeyboardButton(user_page.page.instagram_username)] for user_page in user.user_pages.filter(is_active=True)
    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def inquiry():
    buttons = [
        [KeyboardButton(texts.DONE_INQUIRY),
         KeyboardButton(texts.BACK)
         ],

    ]
    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def order_action():
    buttons = [
        [KeyboardButton(texts.LIKE),
         KeyboardButton(texts.COMMENT),
         KeyboardButton(texts.FOLLOW)
         ],

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
