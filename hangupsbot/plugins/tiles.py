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
    feedna = feedparser.parse("https://wazestatus.wordpress.com/category/main/north-america-tile-updates/feed/")
    feedintl = feedparser.parse("https://wazestatus.wordpress.com/category/main/international-tile-updates/feed/")
    nadate = None
    intldate = None
    naposteddate = None
    intlposteddate = None

    reg = re.compile("((January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4} \d{2}:\d{2} UTC)")

    for num in range(1, 4):
        if reg.search(feedna.entries[num].content[0].value) is not None:
            nadate = reg.search(feedna.entries[num].content[0].value).groups(1)
            naposteddate = datetime.fromtimestamp(mktime(feedna.entries[num].published_parsed))

        if reg.search(feedintl.entries[num].content[0].value) is not None:
            intldate = reg.search(feedintl.entries[num].content[0].value).groups(1)
            intlposteddate = datetime.fromtimestamp(mktime(feedintl.entries[num].published_parsed))

        if nadate is not None and intldate is not None:
            break

    if nadate is None:
        nadate = ["(not found)"]
        naposteddate = datetime(1, 1, 1)
    if intldate is None:
        intldate = ["(not found)"]
        intlposteddate = datetime(1, 1, 1)

    segments = [hangups.ChatMessageSegment("NA: ", is_bold=True),
                hangups.ChatMessageSegment(nadate[0]),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("(update performed: ", is_italic=True),
                hangups.ChatMessageSegment(naposteddate.strftime("%b %d, %Y %H:%M UTC" + ")"), is_italic=True),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("INTL: ", is_bold=True),
                hangups.ChatMessageSegment(intldate[0]),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("(update performed: ", is_italic=True),
                hangups.ChatMessageSegment(intlposteddate.strftime("%b %d, %Y %H:%M UTC") + ")", is_italic=True),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("Full information: "),
                hangups.ChatMessageSegment("https://wazestatus.wordpress.com",
                                           link_target="https://wazestatus.wordpress.com")]

    yield from bot.coro_send_message(event.conv, segments, context={"parser": True})
