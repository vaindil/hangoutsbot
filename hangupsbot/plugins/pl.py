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
    if not inp:
        yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> no message was provided')
        return

    fall = re.findall('http(?:s)?:\/\/(?:www\.)?goo\.gl\/\S+', inp)
    if fall:
        for url in fall:
            inp += ' ' + requests.get(url.strip()).url

    fall = re.findall('http(?:s)?:\/\/(?:www\.)?j\.mp\/\S+', inp)
    if fall:
        for url in fall:
            inp += ' ' + requests.get(url.strip()).url

    fall = re.findall('http(?:s)?:\/\/(?:www\.)?bit\.ly\/\S+', inp)
    if fall:
        for url in fall:
            inp += ' ' + requests.get(url.strip()).url

    fall = re.findall('http(?:s):\/\/(?:www|editor-beta)\.waze\.com\/editor\S+', inp)
    if fall:
        for url in fall:
            inter.append(requests.get(url.strip()).url)

    if inter is None or not inter:
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
