import logging

import requests
import hangups
import plugins

logger = logging.getLogger(__name__)


def _initialise(bot):
    plugins.register_user_command(["wmeversion"])


def wmeversion(bot, event, *args):
    prod = requests.get('https://www.waze.com/Descartes/app/info/version')
    beta = requests.get('https://beta.waze.com/Descartes/app/info/version')

    if prod:
        prodJson = prod.json()
        prodTime = prodJson['time']
        prodVersion = prodJson['version']
    else:
        prodTime = 'Error getting version'
        prodVersion = '(not my fault, I promise!)'

    if beta:
        betaJson = beta.json()
        betaTime = betaJson['time']
        betaVersion = betaJson['version']
    else:
        betaTime = 'Error getting version'
        betaVersion = '(not my fault, I promise!)'

    segments = [hangups.ChatMessageSegment('Prod: ', is_bold=True),
                hangups.ChatMessageSegment('v' + prodVersion),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('(' + prodTime + ')', is_italic=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Beta: ', is_bold=True),
                hangups.ChatMessageSegment('v' + betaVersion),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('(' + betaTime + ')', is_italic=True)]

    yield from bot.coro_send_message(event.conv, segments, context={"parser": True})
