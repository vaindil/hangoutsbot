import logging
import hangups
import re

import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_handler(profile, type="message")


def profile(bot, event, *args):
    """get information about a user"""

    if not isinstance(event.conv_event, hangups.ChatMessageEvent):
        return

    if not event.text.startswith("!profile"):
        return

    if event.text == "!profile" or event.text == "!profiles":
        yield from bot.coro_send_message(event.conv, "<b>profile:</b> provide a username to get links to its profiles")
        return

    if event.text.startswith("!profile "):
        un = event.text[9:].strip()
    elif event.text.startswith("!profiles "):
        un = event.text[10:].strip()
    else:
        return

    r = re.compile(r'<.*?>')
    un = r.sub('', un)

    if un.isspace() or not un:
        yield from bot.coro_send_message(event.conv, "<b>profile:</b> provide a username to get links to its profiles")
        return

    if " " in un:
        yield from bot.coro_send_message(event.conv, "<b>profile:</b> username cannot contain a space")
        return

    rstr = "<b>Links for " + un + ":</b><br />"
    rstr += "<a href=\"https://www.waze.com/user/editor/" + un + "\">Editor profile</a><br />"
    rstr += "<a href=\"https://www.waze.com/forum/memberlist.php?mode=viewprofile&un=" + un + "\">Forum profile</a><br />"
    rstr += "<a href=\"https://wiki.waze.com/wiki/User:" + un + "\">Wiki profile</a><br />"
    rstr += "<i>These links will not work if the profile does not exist.</i>"

    yield from bot.coro_send_message(event.conv, rstr)
