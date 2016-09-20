import logging
import requests
from bs4 import BeautifulSoup
import jellyfish

import plugins

logger = logging.getLogger(__name__)


def glossary(bot, event, *args):
    spjoin = ' '.join(args)
    matches = []
    url = 'https://wazeopedia.waze.com/wiki/USA/Glossary'
    if spjoin == '':
        yield from bot.coro_send_message(event.conv, '<b>glossary</b> - look up a word or phrase in the wiki glossary at ' + url)
        return
    r = requests.get(url).text
    page = BeautifulSoup(r, 'html.parser')

    exactmatch = False

    for entry in page.find_all('tr', valign='top'):
        child = entry.contents[1]
        for span in child.find_all('span'):
            tmp = jellyfish.jaro_winkler(str(span['id']).lower(), spjoin.lower())

            if tmp >= 0.75:
                matches.append([round(tmp * 100), span['id'], child.b.string])

                if tmp == 1.0:
                    matches = [[100, span['id'], child.b.string]]
                    exactmatch = True
                    break

        if exactmatch:
            break

        tmpb = entry.contents[1].find('b').string
        tmp2 = jellyfish.jaro_winkler(tmpb.lower(), spjoin.lower())

        if tmp2 >= 0.75:
            matches.append([round(tmp2 * 100), tmpb, tmpb])

    if len(matches) == 0:
        yield from bot.coro_send_message(event.conv, 'No match found for term: <b>' + spjoin + '</b>. ' + 
                                                     'The glossary page is at ' + url)
        return

    for match in matches:
        if match[0] == 100:
            yield from bot.coro_send_message(event.conv, '<b>' + match[2] + '</b>: ' + url + 
                                                         '#' + match[1].replace(' ', '_'))
            return

    yield from bot.coro_send_message(event.conv, 'No exact matches found for <b>' + spjoin + 
                                                 '</b>. Did you mean:')

    printed = []
    count = 0
    for i in range(99, 75, -1):
        for match in matches:
            if match[0] == i:
                if count == 4:
                    yield from bot.coro_send_message(event.conv, '<i>(only top 4 matches shown)</i>')
                    return
                if not match[2] in printed:
                    count += 1
                    yield from bot.coro_send_message(event.conv, '<b>' + match[2] + '</b>: ' + 
                                                    url + '#' + match[1].replace(' ', '_'))
                    printed.append(match[2])


def _initialise(bot):
    plugins.register_user_command(['glossary'])
