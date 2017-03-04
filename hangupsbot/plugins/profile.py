import logging
import hangups
import requests

import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_user_command(['profile'])


def profile(bot, event, *args):
    """get information about a user"""

    if not isinstance(event.conv_event, hangups.ChatMessageEvent):
        return

    un = ' '.join(args).strip()

    if un.isspace() or not un:
        yield from bot.coro_send_message(event.conv, '<b>profile:</b> provide a username to get links to its profiles')
        return

    if ' ' in un:
        yield from bot.coro_send_message(event.conv, '<b>profile:</b> username cannot contain a space')
        return

    editorurl = 'https://www.waze.com/user/editor/' + un
    segments = [hangups.ChatMessageSegment('Links for ' + un + ': ', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Editor profile', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(editorurl, link_target=editorurl),
                hangups.ChatMessageSegment(' (may not exist)', is_italic=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]

    forumurl = 'https://www.waze.com/forum/memberlist.php?mode=viewprofile&un=' + un
    try:
        r = requests.get(forumurl, timeout=8).status_code
    except requests.exceptions.Timeout:
        r = 999

    if r == 200:
        segments.append(hangups.ChatMessageSegment('Forum profile', is_bold=True))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        segments.append(hangups.ChatMessageSegment(forumurl, link_target=forumurl))
    elif r == 404:
        segments.append(hangups.ChatMessageSegment('(no forum profile)', is_italic=True))
    elif r == 999:
        segments.append(hangups.ChatMessageSegment('(error checking forum profile)', is_italic=True))

    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))

    wikiurl = 'https://wazeopedia.waze.com/wiki/USA/User:' + un
    try:
        r = requests.get(wikiurl, timeout=8).status_code
    except requests.exceptions.Timeout:
        r = 999

    if r == 200:
        segments.append(hangups.ChatMessageSegment('Wiki profile', is_bold=True))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        segments.append(hangups.ChatMessageSegment(wikiurl, link_target=wikiurl))
    elif r == 404:
        segments.append(hangups.ChatMessageSegment('(no wiki profile)', is_italic=True))
    elif r == 999:
        segments.append(hangups.ChatMessageSegment('(error checking wiki profile)', is_italic=True))

    yield from bot.coro_send_message(event.conv, segments)

    # yield from bot.coro_send_message(event.conv, rstr)
