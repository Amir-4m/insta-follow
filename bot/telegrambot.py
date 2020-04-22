import logging

from telegram.ext.dispatcher import run_async

from .decorators import add_session
from . import texts
from apps.instagram_app.models import InstaPage

logger = logging.getLogger(__name__)


@run_async
@add_session(clear=True)
def start(bot, update, session):
    user = session.get("user")
    if InstaPage.objects.filter(owner=user).exists():
        bot.send_message(chat_id=update.effective_user.id,
                         text=texts.START_USER_HAS_PAGE.format(user.first_name),
                         )
    else:
        bot.send_message(chat_id=update.effective_user.id,
                         text=texts.START_USER_HAS_NO_PAGE.format(user.first_name),
                         )


@run_async
@add_session(clear=True)
def stop(bot, update, session):
    pass


@run_async
@add_session
def dispatcher(bot, update, session):
    pass


@add_session
@run_async
def call_state_function(bot, update, session):
    pass
