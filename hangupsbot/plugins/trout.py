import logging
import hangups
import re

import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_handler(trout, type="message")


def trout(bot, event, *args):
    """slap a user with a large trout"""

    if not isinstance(event.conv_event, hangups.ChatMessageEvent):
        return

    if not event.text.startswith("/slap "):
        return

    r = re.compile(r'<.*?>')
    fname = event.user.first_name
    toslap = event.text[5:].strip()
    toslap = r.sub('', toslap)

    yield from bot.coro_send_message(event.conv, fname + " slaps " + toslap + " around a bit with a large trout.")
