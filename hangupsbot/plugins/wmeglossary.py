import logging
import requests
from bs4 import BeautifulSoup
import jellyfish

import plugins

logger = logging.getLogger(__name__)


def glossary(bot, event, *args):
    spjoin = " ".join(args)
    matches = {}
    url = "https://wiki.waze.com/wiki/Glossary"
    if spjoin == "":
        yield from bot.coro_send_message(event.conv, '<b>glossary</b> - look up a word or phrase in the wiki glossary at ' + url)
        return
    r = requests.get(url).text
    page = BeautifulSoup(r, 'html.parser')

    for entry in page.find_all('tr', valign='top'):
        child = entry.contents[1]
        for span in child.find_all('span'):
            tmp = jellyfish.jaro_winkler(str(span['id']).lower(), spjoin.lower())
            if tmp >= 0.75:
                matches[round(tmp * 100)] = [span['id'], child.b.string]
                break

        tmpb = entry.contents[1].find('b').string
        tmp2 = jellyfish.jaro_winkler(tmpb.lower(), spjoin.lower())
        if tmp2 >= 0.75:
            matches[round(tmp2 * 100)] = [tmpb, '<b>' + tmpb + '</b>']

    if len(matches) == 0:
        yield from bot.coro_send_message(event.conv, "No match found for term: <b>" + spjoin + '</b>. The glossary page'
                                                                                               ' is at ' + url)
        return

    if 100 in matches:
        yield from bot.coro_send_message(event.conv,
                                         '<b>' + matches[100][1] + "</b>: " + url + "#" + matches[100][0].replace(' ',
                                                                                                                  '_'))
        return

    yield from bot.coro_send_message(event.conv, 'No exact matches found for <b>' + spjoin + '</b>. Did you mean:')

    count = 0
    for i in range(99, 75, -1):
        if i in matches:
            if count == 4:
                yield from bot.coro_send_message(event.conv, '<i>(only top 4 matches shown)</i>')
                return
            count += 1
            yield from bot.coro_send_message(event.conv,
                                             '<b>' + matches[i][1] + '</b>: ' + url + '#' + matches[i][0].replace(' ',
                                                                                                                  '_'))


def _initialise(bot):
    plugins.register_user_command(["glossary"])
