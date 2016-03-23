import logging
import re
import requests

import hangups
import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_user_command(["pl"])


def pl(bot, event, *args):
    inp = ' '.join(args).strip()
    inter = []
    htc = re.compile('http(?:s)?:\/\/')
    msgprinted = False
    if not inp:
        yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> no message was provided')
        return

    fall = re.findall('(?:http(?:s)?:\/\/)?(?:www\.)?goo\.gl\/\S+', inp)
    if fall:
        for url in fall:
            result = checkurl(url, htc)
            if result == 'BOTTIMEOUTERROR':
                msgprinted = True
                yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> error fetching URL ' + url + ' (their fault, not mine!)')
            else:
                inp += ' ' + result

    fall = re.findall('(?:http(?:s)?:\/\/)?(?:www\.)?j\.mp\/\S+', inp)
    if fall:
        for url in fall:
            result = checkurl(url, htc)
            if result == 'BOTTIMEOUTERROR':
                msgprinted = True
                yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> error fetching URL ' + url + ' (their fault, not mine!)')
            else:
                inp += ' ' + result

    fall = re.findall('(?:http(?:s)?:\/\/)?(?:www\.)?bit\.ly\/\S+', inp)
    if fall:
        for url in fall:
            result = checkurl(url, htc)
            if result == 'BOTTIMEOUTERROR':
                msgprinted = True
                yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> error fetching URL ' + url + ' (their fault, not mine!)')
            else:
                inp += ' ' + result

    fall = re.findall('(?:http(?:s)?:\/\/)?(?:www\.)?bit\.do\/\S+', inp)
    if fall:
        for url in fall:
            result = checkurl(url, htc)
            if result == 'BOTTIMEOUTERROR':
                msgprinted = True
                yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> error fetching URL ' + url + ' (their fault, not mine!)')
            else:
                inp += ' ' + result

    fall = re.findall('(?:http(?:s)?:\/\/)?(?:www\.)?tinyurl\.com\/\S+', inp)
    if fall:
        for url in fall:
            result = checkurl(url, htc)
            if result == 'BOTTIMEOUTERROR':
                msgprinted = True
                yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> error fetching URL ' + url + ' (their fault, not mine!)')
            else:
                inp += ' ' + result

    fall = re.findall('(?:http(?:s):\/\/)?(?:www\.|editor-beta\.)?waze\.com\/editor\S+', inp)
    if fall:
        for url in fall:
            if htc.match(url) is None:
                if not url.startswith('www.') and not url.startswith('editor-beta.'):
                    url = 'www.' + url
                url = 'https://' + url
            inter.append(url)

    if (inter is None or not inter) and not msgprinted:
        yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> no PL found')
        return

    for f in inter:
        f = re.sub('(&|&amp;)mapProblemFilter=(0|1|true|false)', '', f)
        f = re.sub('(&|&amp;)mapUpdateRequestFilter=(0|1|true|false)', '', f)
        f = re.sub('(&|&amp;)venueFilter=(0|1|true|false)', '', f)
        f = re.sub('(&|&amp;)problemsFilter=(0|1|true|false)', '', f)
        f = re.sub('(&|&amp;)update_requestsFilter=(0|1|true|false)', '', f)
        f = re.sub('&amp;&amp;', '&amp;', f)
        f = re.sub('layers=[0-9]+', '', f)
        f = re.sub('%\S*', '', f)
        f = re.sub('\[\S*', '', f)
        f = re.sub('\]\S*', '', f)
        f = re.sub('b=[01]+', '', f)
        f = re.sub('&&', '&', f)
        f = re.sub('&$', '', f)

        yield from bot.coro_send_message(event.conv, f.strip())

def checkurl(url, regex):
    if regex.match(url) is None:
        url = 'https://' + url
    try:
        chk = ' ' + requests.get(url.strip(), timeout=8).url
    except requests.exceptions.Timeout:
        chk = 'BOTTIMEOUTERROR'
    return chk