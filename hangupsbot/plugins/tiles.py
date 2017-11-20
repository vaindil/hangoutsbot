import logging
import re
import time
from time import mktime
from datetime import datetime

import feedparser
import hangups
import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_user_command(["tiles"])


def tiles(bot, event, *args):
    feed = feedparser.parse("https://status.waze.com/feeds/posts/default")
    na = None
    intl = None
    nadate = None
    intldate = None
    naposteddate = None
    intlposteddate = None

    reg = re.compile("((January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4} \d{2}:\d{2} UTC)")

    for num in range(0, 14):
        if na is None and feed.entries[num].title.startswith('NA'):
            na = feed.entries[num]
        if intl is None and feed.entries[num].title.startswith('INTL'):
            intl = feed.entries[num]
        if na is not None and intl is not None:
            break

    if na is None:
        nadate = naposteddate = "N/A"
    else:
        if reg.search(na.content[0].value) is not None:
            nadate = reg.search(na.content[0].value).groups(1)[0]
            naposteddate = datetime.fromtimestamp(mktime(na.published_parsed)).strftime("%b %d, %Y %H:%M UTC")

    if intl is None:
        intldate = intlposteddate = "N/A"
    else:
        if reg.search(intl.content[0].value) is not None:
            intldate = reg.search(intl.content[0].value).groups(1)[0]
            intlposteddate = datetime.fromtimestamp(mktime(intl.published_parsed)).strftime("%b %d, %Y %H:%M UTC")

    segments = [hangups.ChatMessageSegment("NA: ", is_bold=True),
                hangups.ChatMessageSegment(nadate),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("(update performed: ", is_italic=True),
                hangups.ChatMessageSegment(naposteddate, is_italic=True),
                hangups.ChatMessageSegment(")", is_italic=True),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("INTL: ", is_bold=True),
                hangups.ChatMessageSegment(intldate),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("(update performed: ", is_italic=True),
                hangups.ChatMessageSegment(intlposteddate, is_italic=True),
                hangups.ChatMessageSegment(")", is_italic=True),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("Full information: "),
                hangups.ChatMessageSegment("https://status.waze.com",
                                           link_target="https://status.waze.com")]

    yield from bot.coro_send_message(event.conv, segments, context={"parser": True})
