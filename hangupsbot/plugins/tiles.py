import logging
import re

import feedparser
import hangups
import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_user_command(["tiles"])


def tiles(bot, event, *args):
    feedna = feedparser.parse("https://wazestatus.wordpress.com/category/main/north-america-tile-updates/feed/")
    feedintl = feedparser.parse("https://wazestatus.wordpress.com/category/main/international-tile-updates/feed/")

    reg = re.compile("((January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4} \d{2}:\d{2} UTC)")
    nadate = reg.search(feedna.entries[0].content[0].value).groups(1)
    intldate = reg.search(feedintl.entries[0].content[0].value).groups(1)

    segments = [hangups.ChatMessageSegment("NA: ", is_bold=True),
                hangups.ChatMessageSegment(nadate[0]),
                hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment("INTL: ", is_bold=True),
                hangups.ChatMessageSegment(intldate[0])]

    yield from bot.coro_send_message(event.conv, segments)