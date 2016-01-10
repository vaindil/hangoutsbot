import logging
import re
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

    reg = re.compile("((January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4} \d{2}:\d{2} UTC)")
    nadate = reg.search(feedna.entries[0].content[0].value).groups(1)
    intldate = reg.search(feedintl.entries[0].content[0].value).groups(1)
    naposteddate = datetime.fromtimestamp(mktime(feedna.entries[0].published_parsed))
    intlposteddate = datetime.fromtimestamp(mktime(feedintl.entries[0].published_parsed))

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
                hangups.ChatMessageSegment("Full information: https://wazestatus.wordpress.com")]

    yield from bot.coro_send_message(event.conv, segments, context={"parser": True})
