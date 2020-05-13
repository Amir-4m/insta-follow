from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from bot import texts


def start():
    button = [
        [KeyboardButton(texts.CHOICE_PROFILE)],
        [KeyboardButton(texts.CHOICE_CREATE_ORDER)],
        [KeyboardButton(texts.CHOICE_GET_ORDERS)],
        [KeyboardButton(texts.CHOICE_ADD_PAGE)],
        [KeyboardButton(texts.CHOICE_DELETE_PAGE)],
        [KeyboardButton(texts.CHOICE_COLLECT_COIN)]
    ]

    return ReplyKeyboardMarkup(button, one_time_keyboard=True)


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
