import logging

from django.template import Template, Context
from telegram.ext.dispatcher import run_async

from apps.instagram_app.models import UserPage, InstaPage
from apps.instagram_app.services import InstagramAppService
from .decorators import add_session
from . import texts, buttons

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
        result = InstagramAppService.get_page_info(page_id, full_info=True)
        page, i_created = InstaPage.objects.get_or_create(
            instagram_username=page_id,
            instagram_user_id=result[0],
            defaults={
                dict(
                    followers=result[2],
                    following=result[3],
                    post_no=result[4]
                )

            }

        )
        user_page, u_created = UserPage.objects.get_or_create(user=user, page=page)
        if not u_created and user_page.is_active is False:
            user_page.is_active = True
            user_page.save()

        t = Template(texts.PAGE_CREATED)
        c = Context(dict(page=user_page.page))

        bot.send_message(
            text=t.render(c),
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )


@add_session
@run_async
def call_state_function(bot, update, session):
    pass
