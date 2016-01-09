import re
import requests
from bs4 import BeautifulSoup

import plugins


def glossary(bot, event, *args):
    url = "https://wiki.waze.com/wiki/Glossary"
    r = requests.get(url).text
    page = BeautifulSoup(r, 'html.parser')

    if page.find_all(string=re.compile(" ".join(args), re.I)):
        tag = page.find('b', string=re.compile(" ".join(args), re.I))
        termout = str(tag)
        urlout = tag.string.replace(" ", "_")
        yield from bot.coro_send_message(event.conv, termout + ": " + url + "#" + urlout)
    else:
        yield from bot.coro_send_message(event.conv, "<b>No match found for term:</b> " + " ".join(args))


def _initialise(bot):
    plugins.register_user_command(["glossary"])