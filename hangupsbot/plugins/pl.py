import logging
import re
import requests
import urllib.parse

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

    fall = re.findall('(?:http(?:s):\/\/)?(?:www\.|beta\.)?waze\.com\/(?:.*?\/)?editor\S+', inp)
    if fall:
        for url in fall:
            if re.search('\/user\/', url):
                continue
            if htc.match(url) is None:
                if not url.startswith('www.'):
                    url = 'www.' + url
                url = 'https://' + url
            inter.append(url)

    if  (inter is None or not inter) and not msgprinted:
        yield from bot.coro_send_message(event.conv_id, '<b>Permalink:</b> no PL found')
        return

    url = urllib.parse.unquote(url)
    url = url.replace('beta', 'www', 1)
    fall = re.findall('(?!(?:\?|&))(?:env|lon|lat|zoom|mapUpdateRequest|segments|nodes|venues|cameras|bigJunctions|mapComments)=[a-zA-Z0-9.\-,_\.]+', url)
    if fall:
        url = re.sub('\?.*', '', url, flags=re.DOTALL)
        url += '?'
        for p in fall:
            url += p + '&'
        url = url[:-1]

    yield from bot.coro_send_message(event.conv, url.strip())

def checkurl(url, regex):
    if regex.match(url) is None:
        url = 'https://' + url
    try:
        chk = ' ' + requests.get(url.strip(), timeout=8).url
    except requests.exceptions.Timeout:
        chk = 'BOTTIMEOUTERROR'
    return chk