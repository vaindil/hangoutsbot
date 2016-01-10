import logging
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

import plugins

logger = logging.getLogger(__name__)


def glossary(bot, event, *args):
    spjoin = " ".join(args)
    matches = {}
    url = "https://wiki.waze.com/wiki/Glossary"
    r = requests.get(url).text
    page = BeautifulSoup(r, 'html.parser')

    for entry in page.find_all('tr', valign='top'):
        child = entry.contents[1]
        for span in child.find_all('span'):
            tmp = fuzz.ratio(str(span['id']).lower(), spjoin.lower())
            if tmp >= 80:
                matches[tmp] = [span['id'], child.b.string]

        tmpb = entry.contents[1].find('b').string
        tmp2 = fuzz.ratio(tmpb.lower(), spjoin.lower())
        if tmp2 >= 80:
            matches[tmp2] = [tmpb, '<b>' + tmpb + '</b>']

    if len(matches) == 0:
        yield from bot.coro_send_message(event.conv, "No match found for term: <b>" + spjoin + '</b>')
        return

    if 100 in matches:
        yield from bot.coro_send_message(event.conv, '<b>' + matches[100][1] + "</b>: " + url + "#" + matches[100][0])
        return

    yield from bot.coro_send_message(event.conv, 'No exact matches found for <b>' + spjoin + '</b>. Did you mean:')

    count = 0
    for i in range(99, 80, -1):
        if i in matches:
            if count == 4:
                yield from bot.coro_send_message(event.conv, '<i>(only top 4 matches shown)</i>')
            count += 1
            yield from bot.coro_send_message(event.conv, matches[i][1] + ': ' + url + '#' + matches[i][0])


def _initialise(bot):
    plugins.register_user_command(["glossary"])