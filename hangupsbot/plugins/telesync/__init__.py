# A Sync plugin for Telegram and Hangouts

import os
import logging
import io
import random
import asyncio
import aiohttp

import telepot.aio

import hangups

import plugins

from webbridge import ( WebFramework,
                        FakeEvent )

logger = logging.getLogger(__name__)


# TELEGRAM BOT

class TelegramBot(telepot.aio.Bot):
    def __init__(self, hangupsbot):
        self.config = hangupsbot.config.get_by_path(['telesync'])

        super().__init__(self.config['api_key'])

        if "bot_name" in hangupsbot.config.get_by_path(["telesync"]):
            self.name = hangupsbot.config.get_by_path(["telesync"])["bot_name"]
        else:
            self.name = "bot"

        self.commands = {}

        self.onMessageCallback = TelegramBot.on_message
        self.onPhotoCallback = TelegramBot.on_photo
        self.onStickerCallback = TelegramBot.on_sticker
        self.onUserJoinCallback = TelegramBot.on_user_join
        self.onUserLeaveCallback = TelegramBot.on_user_leave
        self.onLocationShareCallback = TelegramBot.on_location_share
        self.onSupergroupUpgradeCallback = TelegramBot.on_supergroup_upgrade

        self.ho_bot = hangupsbot
        self.chatbridge = BridgeInstance(hangupsbot, "telesync")

    @asyncio.coroutine
    def setup_bot_info(self):
        """Setup bot.id, bot.name and bot.username fields"""

        _bot_data = yield from self.getMe()

        self.id = _bot_data['id']
        self.name = _bot_data['first_name']
        self.username = _bot_data['username']

        logger.info("telepot bot - id: {}, name: {}, username: {}".format( self.id,
                                                                           self.name,
                                                                           self.username ))


    def add_command(self, cmd, func):
        self.commands[cmd] = func

    def remove_command(self, cmd):
        if cmd in self.commands:
            del self.commands[cmd]

    @staticmethod
    def is_command(msg):
        if 'text' in msg:
            if msg['text'].startswith('/'):
                return True
        return False

    @staticmethod
    def parse_command(cmd):
        txt_split = cmd.split()
        return txt_split[0].split("@")[0], txt_split[1:]

    @staticmethod
    def get_user_id(msg):
        if 'from' in msg:
            return str(msg['from']['id'])
        return ""

    @staticmethod
    def get_username(msg, chat_action='from'):
        if 'username' in msg[chat_action]:
            return str(msg[chat_action]['username'])
        return ""

    @staticmethod
    def on_message(bot, chat_id, msg):
        print("[MSG] {uid} : {txt}".format(uid=msg['from']['id'], txt=msg['text']))

    @staticmethod
    def on_photo(bot, chat_id, msg):
        print("[PIC]{uid} : {photo_id}".format(uid=msg['from']['id'], photo_id=msg['photo'][0]['file_id']))

    @staticmethod
    def on_sticker(bot, chat_id, msg):
        print("[STI]{uid} : {file_id}".format(uid=msg['from']['id'], file_id=msg['sticker']['file_id']))

    @staticmethod
    def on_user_join(bot, chat_id, msg):
        print("New User: {name}".format(name=msg['new_chat_member']['first_name']))

    @staticmethod
    def on_user_leave(bot, chat_id, msg):
        print("{name} Left the gorup".format(name=msg['left_chat_member']['first_name']))

    @staticmethod
    def on_location_share(bot, chat_id, msg):
        print("{name} shared a location".format(name=msg['from']['first_name']))

    @staticmethod
    def on_supergroup_upgrade(bot, msg):
        print("Group {old_chat_id} upgraded to supergroup {new_chat_id}".format(old_chat_id=msg['chat']['id'],
                                                                                new_chat_id=msg['migrate_to_chat_id']))

    def set_on_message_callback(self, func):
        self.onMessageCallback = func

    def set_on_photo_callback(self, func):
        self.onPhotoCallback = func

    def set_on_sticker_callback(self, func):
        self.onStickerCallback = func

    def set_on_user_join_callback(self, func):
        self.onUserJoinCallback = func

    def set_on_user_leave_callback(self, func):
        self.onUserLeaveCallback = func

    def set_on_location_share_callback(self, func):
        self.onLocationShareCallback = func

    def set_on_supergroup_upgrade_callback(self, func):
        self.onSupergroupUpgradeCallback = func

    def is_telegram_admin(self, user_id):
        tg_conf = _telesync_config(self.ho_bot)
        if "admins" in tg_conf and user_id in tg_conf["admins"]:
            return True
        else:
            return False

    @asyncio.coroutine
    def get_hangouts_image_id_from_telegram_photo_id(self, photo_id):
        metadata = yield from self.getFile(photo_id)
        photo_path = "https://api.telegram.org/file/bot{}/{}".format(self.config['api_key'], metadata["file_path"])
        ho_photo_id = yield from self.ho_bot.call_shared("image_upload_single", photo_path)
        return ho_photo_id

    @asyncio.coroutine
    def handle(self, msg):

        if 'migrate_to_chat_id' in msg:
            yield from self.onSupergroupUpgradeCallback(self, msg)

        else:
            flavor = telepot.flavor(msg)

            if flavor == "chat":  # chat message
                content_type, chat_type, chat_id = telepot.glance(msg)
                if content_type == 'text':
                    if TelegramBot.is_command(msg):  # bot command
                        cmd, params = TelegramBot.parse_command(msg['text'])
                        user_id = TelegramBot.get_user_id(msg)
                        args = {'params': params, 'user_id': user_id, 'chat_type': chat_type}
                        if cmd in self.commands:
                            yield from self.commands[cmd](self, chat_id, args)
                        else:
                            if "be_quiet" in self.config and self.config["be_quiet"]:
                                pass
                            else:
                                yield from self.sendMessage(chat_id, "Unknown command: {cmd}".format(cmd=cmd))

                    else:  # plain text message
                        yield from self.onMessageCallback(self, chat_id, msg)

                elif content_type == 'location':
                    yield from self.onLocationShareCallback(self, chat_id, msg)

                elif content_type == 'new_chat_member':
                    yield from self.onUserJoinCallback(self, chat_id, msg)

                elif content_type == 'left_chat_member':
                    yield from self.onUserLeaveCallback(self, chat_id, msg)

                elif content_type == 'photo':
                    yield from self.onPhotoCallback(self, chat_id, msg)

                elif content_type == 'sticker':
                    config = _telesync_config(tg_bot.ho_bot)
                    if "enable_sticker_sync" in config and config["enable_sticker_sync"]:
                        yield from self.onStickerCallback(self, chat_id, msg)

            elif flavor == "inline_query":  # inline query e.g. "@gif cute panda"
                query_id, from_id, query_string = telepot.glance(msg, flavor=flavor)
                print("inline_query")

            elif flavor == "chosen_inline_result":
                result_id, from_id, query_string = telepot.glance(msg, flavor=flavor)
                print("chosen_inline_result")

            else:
                raise telepot.BadFlavor(msg)

def tg_util_get_group_name(msg):
    """
    :param msg: msg object from telepot
    :return: if msg sent to a group, will return Groups name, return msg type otherwise
    """
    title = msg['chat']['type']
    # if title == 'group' or title == 'supergroup':
    if title in ['group', 'supergroup']:
        title = msg['chat']['title']
    return title

def tg_util_get_photo_caption(msg):
    caption = ""
    if 'caption' in msg:
        caption = msg['caption']

    return caption

def tg_util_get_photo_list(msg):
    photos = []
    if 'photo' in msg:
        photos = msg['photo']
        photos = sorted(photos, key=lambda k: k['width'])

    return photos

def tg_util_location_share_get_lat_long(msg):
    lat = ""
    long = ""
    if 'location' in msg:
        loc = msg['location']
        lat = loc['latitude']
        long = loc['longitude']

    return lat, long

def tg_util_create_gmaps_url(lat, long, https=True):
    return "{https}://maps.google.com/maps?q={lat},{long}".format(https='https' if https else 'http', lat=lat,
                                                                  long=long)

def tg_util_create_telegram_me_link(username, https=True):
    return "{https}://telegram.me/{username}".format(https='https' if https else 'http', username=username)

def tg_util_sync_get_user_name(msg, chat_action='from'):
    profile_dict = tg_bot.ho_bot.memory.get_by_path(['profilesync'])['tg2ho']
    username = TelegramBot.get_username(msg, chat_action=chat_action)

    if( str(msg['from']['id']) in profile_dict
            and "user_gplus" in profile_dict[str(msg['from']['id'])] ):

        user_html = profile_dict[str(msg['from']['id'])]['user_text']
    else:
        url = tg_util_create_telegram_me_link(username)
        # hangouts used to support embedded links,
        #   no longer displays them unless the url matches visible text
        user_html = "{}".format(msg[chat_action]['first_name'])

    return msg[chat_action]['first_name'] if username == "" else user_html

@asyncio.coroutine
def tg_on_message(tg_bot, tg_chat_id, msg):
    # map telegram group id to hangouts group id
    tg_chat_id = str(tg_chat_id)
    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']
    if tg_chat_id not in tg2ho_dict:
        return

    ho_conv_id = tg2ho_dict[tg_chat_id]
    user = tg_util_sync_get_user_name(msg)
    chat_title = tg_util_get_group_name(msg)

    config = _telesync_config(tg_bot.ho_bot)

    original_message = msg["text"]
    formatted_line = "<b>{}</b>: {}".format( user,
                                             msg["text"] )

    if("sync_chat_titles" not in config or config["sync_chat_titles"]):
        if chat_title:
            formatted_line = "<b>{}</b> ({}): {}".format( user,
                                                          chat_title,
                                                          msg["text"] )

    if 'sync_reply_to' in config and config['sync_reply_to'] and 'reply_to_message' in msg:
        """specialised formatting for reply-to telegram messages"""

        content_type, chat_type, chat_id = telepot.glance(msg['reply_to_message'])

        if msg['reply_to_message']['from']['first_name'].lower() == tg_bot.name.lower():
            r_text = ( msg['reply_to_message']['text'].split(':')
                       if 'text' in msg['reply_to_message'] else content_type )

            r2_user = r_text[0]
        else:
            r_text = ( ['', msg['reply_to_message']['text']]
                       if 'text' in msg['reply_to_message'] else content_type )

            r2_user = tg_util_sync_get_user_name(msg['reply_to_message'])

        if content_type == 'text':
            r2_text = r_text[1]
            r2_text = ( r2_text
                        if len(r2_text) < 30 else r2_text[0:30] + "..." )

        else:
            r2_text = content_type

        r2_format = "\n| <i><b>{}</b></i>:\n| <i>{}</i>\n{}"
        original_message = r2_format.format(r2_user, r2_text, original_message)
        formatted_line = r2_format.format(r2_user, r2_text, formatted_line)

        logger.info("REPLY-TO {}: {}".format( ho_conv_id,
                                              repr(formatted_line) ))
    else:
        logger.info("STANDARD {}: {}".format( ho_conv_id,
                                              repr(formatted_line) ))

    yield from tg_bot.chatbridge._send_to_internal_chat(
        ho_conv_id,
        FakeEvent(
            text = formatted_line,
            user = user,
            passthru = {
                "original_request": {
                    "message": original_message,
                    "image_id": None,
                    "segments": None,
                    "user": user },
                "chatbridge": {
                    "source_title": chat_title },
                "norelay": [ tg_bot.chatbridge.plugin_name ] }))


@asyncio.coroutine
def tg_on_sticker(tg_bot, tg_chat_id, msg):
    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']

    if str(tg_chat_id) in tg2ho_dict:
        ho_conv_id = tg2ho_dict[str(tg_chat_id)]

        chat_title = tg_util_get_group_name(msg)

        user = tg_util_sync_get_user_name(msg)
        text = "uploading sticker from <b>{}</b> in <b>{}</b>...".format(
            tg_util_sync_get_user_name(msg),
            chat_title )

        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = text,
                user = user,
                passthru = {
                    "original_request": {
                        "message": text,
                        "image_id": None,
                        "segments": None,
                        "user": user },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        ho_photo_id = yield from tg_bot.get_hangouts_image_id_from_telegram_photo_id(msg['sticker']['file_id'])

        text = "sent {} sticker".format(msg["sticker"]['emoji'])
        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = text,
                user = user,
                passthru = {
                    "original_request": {
                        "message": text,
                        "image_id": ho_photo_id,
                        "segments": None,
                        "user": user },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        logger.info("sticker posted to hangouts")


@asyncio.coroutine
def tg_on_photo(tg_bot, tg_chat_id, msg):
    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']

    if str(tg_chat_id) in tg2ho_dict:
        ho_conv_id = tg2ho_dict[str(tg_chat_id)]

        chat_title = tg_util_get_group_name(msg)

        user = tg_util_sync_get_user_name(msg)
        text = "uploading photo from <b>{}</b> in <b>{}</b>...".format(
            user,
            chat_title )

        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = text,
                user = user,
                passthru = {
                    "original_request": {
                        "message": text,
                        "image_id": None,
                        "segments": None,
                        "user": user },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        tg_photos = tg_util_get_photo_list(msg)
        tg_photo_id = tg_photos[len(tg_photos) - 1]['file_id']
        ho_photo_id = yield from tg_bot.get_hangouts_image_id_from_telegram_photo_id(tg_photo_id)

        text = "sent a photo"
        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = text,
                user = user,
                passthru = {
                    "original_request": {
                        "message": text,
                        "image_id": ho_photo_id,
                        "segments": None,
                        "user": user },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        logger.info("photo posted to hangouts")


@asyncio.coroutine
def tg_on_user_join(tg_bot, tg_chat_id, msg):
    config_dict = _telesync_config(tg_bot.ho_bot)
    if 'sync_join_messages' not in config_dict or not config_dict['sync_join_messages']:
        return

    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']

    if str(tg_chat_id) in tg2ho_dict:
        ho_conv_id = tg2ho_dict[str(tg_chat_id)]
        chat_title = tg_util_get_group_name(msg)

        formatted_line = "<b>{}</b> joined <b>{}</b>".format(
            tg_util_sync_get_user_name(msg, chat_action='new_chat_member'),
            chat_title )

        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = formatted_line,
                user = "telesync",
                passthru = {
                    "original_request": {
                        "message": formatted_line,
                        "image_id": None,
                        "segments": None,
                        "user": "telesync" },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        logger.info("join {} {}".format( ho_conv_id,
                                         formatted_line ))


@asyncio.coroutine
def tg_on_user_leave(tg_bot, tg_chat_id, msg):
    config_dict = _telesync_config(tg_bot.ho_bot)
    if 'sync_join_messages' not in config_dict or not config_dict['sync_join_messages']:
        return

    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']

    if str(tg_chat_id) in tg2ho_dict:
        ho_conv_id = tg2ho_dict[str(tg_chat_id)]
        chat_title = tg_util_get_group_name(msg)

        formatted_line = "<b>{}</b> left <b>{}</b>".format(
            tg_util_sync_get_user_name(msg, chat_action='left_chat_member'),
            chat_title )

        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = formatted_line,
                user = "telesync",
                passthru = {
                    "original_request": {
                        "message": formatted_line,
                        "image_id": None,
                        "segments": None,
                        "user": "telesync" },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        logger.info("left {} {}".format( ho_conv_id,
                                         formatted_line ))


@asyncio.coroutine
def tg_on_location_share(tg_bot, tg_chat_id, msg):
    lat, long = tg_util_location_share_get_lat_long(msg)
    maps_url = tg_util_create_gmaps_url(lat, long)

    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']
    config = _telesync_config(tg_bot.ho_bot)

    if str(tg_chat_id) in tg2ho_dict:
        chat_title = tg_util_get_group_name(msg)

        user = tg_util_sync_get_user_name(msg)
        text = maps_url

        formatted_line = "<b>{}</b>: {}".format( user,
                                                 text )

        ho_conv_id = tg2ho_dict[str(tg_chat_id)]

        yield from tg_bot.chatbridge._send_to_internal_chat(
            ho_conv_id,
            FakeEvent(
                text = formatted_line,
                user = user,
                passthru = {
                    "original_request": {
                        "message": text,
                        "image_id": None,
                        "segments": None,
                        "user": user },
                    "chatbridge": {
                        "source_title": chat_title },
                    "norelay": [ tg_bot.chatbridge.plugin_name ] }))

        logger.info("location {} {}".format( ho_conv_id,
                                             text ))


@asyncio.coroutine
def tg_on_supergroup_upgrade(bot, msg):
    old_chat_id = str(msg['chat']['id'])
    new_chat_id = str(msg['migrate_to_chat_id'])

    memory = bot.ho_bot.memory.get_by_path(['telesync'])
    tg2ho_dict = memory['tg2ho']
    ho2tg_dict = memory['ho2tg']

    if old_chat_id in tg2ho_dict:

        ho_conv_id = tg2ho_dict[old_chat_id]
        ho2tg_dict[ho_conv_id] = new_chat_id
        tg2ho_dict[new_chat_id] = ho_conv_id

        del tg2ho_dict[old_chat_id]

        new_memory = {'tg2ho': tg2ho_dict, 'ho2tg': ho2tg_dict}
        bot.ho_bot.memory.set_by_path(['telesync'], new_memory)

        logger.info("SUPERGROUP: {} to {}".format( old_chat_id,
                                                   new_chat_id ))


@asyncio.coroutine
def tg_command_whoami(bot, chat_id, args):
    user_id = args['user_id']
    chat_type = args['chat_type']
    if 'private' == chat_type:
        yield from bot.sendMessage(chat_id, "Your Telegram user id: {user_id}".format(user_id=user_id))
    else:
        yield from bot.sendMessage(chat_id, "This command can only be used in private chats")


@asyncio.coroutine
def tg_command_whereami(bot, chat_id, args):
    user_id = args['user_id']
    if bot.is_telegram_admin(user_id):
        yield from bot.sendMessage(chat_id, "current group's id: '{chat_id}'".format(chat_id=chat_id))
    else:
        yield from bot.sendMessage(chat_id, "Only admins can do that")


@asyncio.coroutine
def tg_command_set_sync_ho(bot, chat_id, args):  # /setsyncho <hangout conv_id>
    user_id = args['user_id']
    params = args['params']

    if not bot.is_telegram_admin(user_id):
        yield from bot.sendMessage(chat_id, "Only admins can do that")
        return

    if len(params) != 1:
        yield from bot.sendMessage(chat_id, "Illegal or Missing arguments!!!")
        return

    memory = bot.ho_bot.memory.get_by_path(['telesync'])
    tg2ho_dict = memory['tg2ho']
    ho2tg_dict = memory['ho2tg']

    if str(chat_id) in tg2ho_dict:
        yield from bot.sendMessage(chat_id,
                                   "Sync target '{ho_conv_id}' already set".format(ho_conv_id=str(params[0])))

    else:
        tg2ho_dict[str(chat_id)] = str(params[0])
        ho2tg_dict[str(params[0])] = str(chat_id)

        new_memory = {'tg2ho': tg2ho_dict, 'ho2tg': ho2tg_dict}
        bot.ho_bot.memory.set_by_path(['telesync'], new_memory)

        yield from bot.sendMessage(chat_id, "Sync target set to '{ho_conv_id}''".format(ho_conv_id=str(params[0])))


@asyncio.coroutine
def tg_command_clear_sync_ho(bot, chat_id, args):
    user_id = args['user_id']
    if not bot.is_telegram_admin(user_id):
        yield from bot.sendMessage(chat_id, "Only admins can do that")
        return
    memory = bot.ho_bot.memory.get_by_path(['telesync'])
    tg2ho_dict = memory['tg2ho']
    ho2tg_dict = memory['ho2tg']

    if str(chat_id) in tg2ho_dict:
        ho_conv_id = tg2ho_dict[str(chat_id)]
        del tg2ho_dict[str(chat_id)]
        del ho2tg_dict[ho_conv_id]

    new_memory = {'tg2ho': tg2ho_dict, 'ho2tg': ho2tg_dict}
    bot.ho_bot.memory.set_by_path(['telesync'], new_memory)

    yield from bot.sendMessage(chat_id, "Sync target cleared")


@asyncio.coroutine
def tg_command_add_bot_admin(bot, chat_id, args):
    user_id = args['user_id']
    params = args['params']
    chat_type = args['chat_type']

    if 'private' != chat_type:
        yield from bot.sendMessage(chat_id, "This command must be invoked in private chat")
        return

    if not bot.is_telegram_admin(user_id):
        yield from bot.sendMessage(chat_id, "Only admins can do that")
        return

    if len(params) != 1:
        yield from bot.sendMessage(chat_id, "Illegal or Missing arguments!!!")
        return

    tg_conf = _telesync_config(bot.ho_bot)

    text = ""
    if str(params[0]) not in tg_conf['admins']:
        tg_conf['admins'].append(str(params[0]))
        bot.ho_bot.config.set_by_path(['telesync'], tg_conf)
        text = "User added to admins"
    else:
        text = "User is already an admin"

    yield from bot.sendMessage(chat_id, text)


@asyncio.coroutine
def tg_command_remove_bot_admin(bot, chat_id, args):
    user_id = args['user_id']
    params = args['params']
    chat_type = args['chat_type']

    if 'private' != chat_type:
        yield from bot.sendMessage(chat_id, "This command must be invoked in private chat")
        return

    if not bot.is_telegram_admin(user_id):
        yield from bot.sendMessage(chat_id, "Only admins can do that")
        return

    if len(params) != 1:
        yield from bot.sendMessage(chat_id, "Illegal or Missing arguments!!!")
        return

    target_user = str(params[0])

    tg_conf = _telesync_config(bot.ho_bot)

    text = ""
    if target_user in tg_conf['admins']:
        tg_conf['admins'].remove(target_user)
        bot.ho_bot.config.set_by_path(['telesync'], tg_conf)
        text = "User removed from admins"
    else:
        text = "User is not an admin"

    yield from bot.sendMessage(chat_id, text)


@asyncio.coroutine
def tg_command_tldr(bot, chat_id, args):
    params = args['params']

    tg2ho_dict = tg_bot.ho_bot.memory.get_by_path(['telesync'])['tg2ho']
    if str(chat_id) in tg2ho_dict:
        ho_conv_id = tg2ho_dict[str(chat_id)]
        tldr_args = {'params': params, 'conv_id': ho_conv_id}
        try:
            text = bot.ho_bot.call_shared("plugin_tldr_shared", bot.ho_bot, tldr_args)
            yield from bot.sendMessage(chat_id, text, parse_mode='HTML')
        except KeyError as ke:
            yield from bot.sendMessage(chat_id, "TLDR plugin is not active. KeyError: {e}".format(e=ke))
    elif str(chat_id) not in tg2ho_dict:
        ho_conv_id = str(chat_id)
        tldr_args = {'params': params, 'conv_id': ho_conv_id}
        try:
            text = bot.ho_bot.call_shared("plugin_tldr_shared", bot.ho_bot, tldr_args)
            yield from bot.sendMessage(chat_id, text, parse_mode='HTML')
        except KeyError as ke:
            yield from bot.sendMessage(chat_id, "TLDR plugin is not active. KeyError: {e}".format(e=ke))


@asyncio.coroutine
def tg_command_sync_profile(bot, chat_id, args):
    if 'private' != args['chat_type']:
        yield from bot.sendMessage(chat_id, "Comand must be run in private chat!")
        return
    tg2ho_dict = bot.ho_bot.memory.get_by_path(['profilesync'])['tg2ho']
    ho2tg_dict = bot.ho_bot.memory.get_by_path(['profilesync'])['ho2tg']
    user_id = args['user_id']
    if str(user_id) in tg2ho_dict:
        yield from bot.sendMessage(chat_id, "Your profile is currently synced, to change this run /unsyncprofile")
        return

    rndm = random.randint(0, 9223372036854775807)
    tg2ho_dict[str(user_id)] = str(rndm)
    ho2tg_dict[str(rndm)] = str(user_id)
    new_memory = {'tg2ho': tg2ho_dict, 'ho2tg': ho2tg_dict}
    print(new_memory)
    bot.ho_bot.memory.set_by_path(['profilesync'], new_memory)

    yield from bot.sendMessage(chat_id, "Paste the following command in the private ho with me")
    yield from bot.sendMessage(chat_id, "/bot syncprofile {}".format(str(rndm)))


@asyncio.coroutine
def tg_command_unsync_profile(bot, chat_id, args):
    if 'private' != args['chat_type']:
        yield from bot.sendMessage(chat_id, "Comand must be run in private chat!")
        return

    tg2ho_dict = bot.ho_bot.memory.get_by_path(['profilesync'])['tg2ho']
    ho2tg_dict = bot.ho_bot.memory.get_by_path(['profilesync'])['ho2tg']
    text = ""
    if args['user_id'] in tg2ho_dict:
        ho_id = tg2ho_dict[str(args['user_id'])]['ho_id']
        del tg2ho_dict[str(args['user_id'])]
        del ho2tg_dict[str(ho_id)]
        new_memory = {'tg2ho': tg2ho_dict, 'ho2tg': ho2tg_dict}
        bot.ho_bot.memory.set_by_path(['profilesync'], new_memory)
        text = "Succsessfully removed sync of your profile."
    else:
        text = "There is no sync setup for your profile."

    yield from bot.sendMessage(chat_id, text)


@asyncio.coroutine
def tg_command_get_me(bot, chat_id, args):
    """
    return Telegram Bot's id, name and username
    :param bot: TelegramBot object
    :param chat_id: chat id
    :param args: other args
    :return: None
    """
    user_id = args['user_id']
    chat_type = args['chat_type']
    if 'private' != chat_type:
        yield from bot.sendMessage(chat_id, "Comand must be run in private chat!")
        return

    if bot.is_telegram_admin(user_id):
        yield from bot.sendMessage(chat_id,
                                   "id: {id}, name: {name}, username: @{username}".format(id=bot.id, name=bot.name,
                                                                                          username=bot.username))
    else:
        yield from bot.sendMessage(chat_id, "Only admins can do that")


# TELEGRAM DEFINITIONS END

# HANGOUTSBOT

tg_bot = None

# (Chat) BridgeInstance

class BridgeInstance(WebFramework):
    def setup_plugin(self):
        self.plugin_name = "telegramTelesync"

    def load_configuration(self, configkey):
        # immediately halt configuration load if it isn't available
        telesync_config = _telesync_config(self.bot)
        if "enabled" not in telesync_config  or not telesync_config["enabled"]:
            return

        # telesync uses bot memory to store its internal locations
        self.configuration = { "config": telesync_config,
                               "memory": self.bot.get_memory_option(configkey) }

        return self.configuration

    def applicable_configuration(self, conv_id):
        """telesync configuration compatibility

        * only 1-to-1 linkages (telegram-ho) allowed
        * utilises memory to store linkages, config.json for global settings"""

        self.load_configuration(self.configkey)

        applicable_configurations = []
        ho2tg_dict = self.configuration["memory"]["ho2tg"]
        if conv_id in ho2tg_dict:
            # combine config.json and memory options to generate a dict
            config_clone = dict(self.configuration["config"])
            config_clone.update({ self.configkey: [ ho2tg_dict[conv_id] ],
                                  "hangouts": [ conv_id ] })
            applicable_configurations.append({ "trigger": conv_id,
                                               "config.json": config_clone })

        return applicable_configurations

    @asyncio.coroutine
    def _send_to_external_chat(self, config, event):
        conv_id = config["trigger"]
        external_ids = config["config.json"][self.configkey]

        user = event.passthru["original_request"]["user"]
        message = event.passthru["original_request"]["message"]

        """migrated from telesync _on_hangouts_message():

        * by this point of execution, applicable_configuration() would have
            already filtered only relevant events
        * telesync configuration only allows 1-to-1 telegram-ho mappings, this
            migrated function supports multiple telegram groups anyway"""

        sync_text = message
        photo_url = None

        has_photo, photo_file_name = yield from _telesync_is_valid_image_link(sync_text)
        if has_photo:
            photo_url = sync_text
            sync_text = "shared an image"

        user_gplus = 'https://plus.google.com/u/0/{}/about'.format(event.user.id_.chat_id)

        preferred_name, nickname, full_name, user_photo_url = self._standardise_bridge_user_details(user)

        chat_title = format(self.bot.conversations.get_name(conv_id))

        if "chatbridge" in event.passthru and event.passthru["chatbridge"]["source_title"]:
            chat_title = event.passthru["chatbridge"]["source_title"]

        if "sync_chat_titles" not in config or config["sync_chat_titles"] and chat_title:
            formatted_text = "<a href=\"{}\">{}</a> ({}): {}".format( user_gplus,
                                                                      preferred_name,
                                                                      chat_title,
                                                                      sync_text )
        else:
            formatted_text = "<a href=\"{}\">{}</a>: {}".format( user_gplus,
                                                                 preferred_name,
                                                                 sync_text )

        # send messages first
        for eid in external_ids:
            yield from tg_bot.sendMessage( eid,
                                           formatted_text,
                                           parse_mode = 'HTML',
                                           disable_web_page_preview = True )

        # send photos
        if has_photo:
            with aiohttp.ClientSession() as session:
                resp = yield from session.get(photo_url)
                raw_data = yield from resp.read()
                resp.close()
                tempfile = io.BytesIO(raw_data)

            for eid in external_ids:
                if photo_file_name.endswith((".gif", ".gifv", ".webm", ".mp4")):
                    yield from tg_bot.sendDocument( eid,
                                                    tempfile )
                else:
                    yield from tg_bot.sendPhoto( eid,
                                                 tempfile )


"""hangoutsbot plugin initialisation"""

def _initialise(bot):
    if not _telesync_config(bot):
        return

    if not bot.memory.exists(['telesync']):
        bot.memory.set_by_path(['telesync'], {'ho2tg': {}, 'tg2ho': {}})

    if not bot.memory.exists(['profilesync']):
        bot.memory.set_by_path(['profilesync'], {'ho2tg': {}, 'tg2ho': {}})

    global tg_bot

    tg_bot = TelegramBot(bot)

    tg_bot.set_on_message_callback(tg_on_message)
    tg_bot.set_on_photo_callback(tg_on_photo)
    tg_bot.set_on_sticker_callback(tg_on_sticker)
    tg_bot.set_on_user_join_callback(tg_on_user_join)
    tg_bot.set_on_user_leave_callback(tg_on_user_leave)
    tg_bot.set_on_location_share_callback(tg_on_location_share)
    tg_bot.set_on_supergroup_upgrade_callback(tg_on_supergroup_upgrade)
    tg_bot.add_command("/whoami", tg_command_whoami)
    tg_bot.add_command("/whereami", tg_command_whereami)
    tg_bot.add_command("/setsyncho", tg_command_set_sync_ho)
    tg_bot.add_command("/clearsyncho", tg_command_clear_sync_ho)
    tg_bot.add_command("/addadmin", tg_command_add_bot_admin)
    tg_bot.add_command("/removeadmin", tg_command_remove_bot_admin)
    tg_bot.add_command("/tldr", tg_command_tldr)
    tg_bot.add_command("/syncprofile", tg_command_sync_profile)
    tg_bot.add_command("/unsyncprofile", tg_command_unsync_profile)
    tg_bot.add_command("/getme", tg_command_get_me)

    plugins.start_asyncio_task(tg_bot.message_loop())
    plugins.start_asyncio_task(tg_bot.setup_bot_info())

    plugins.register_admin_command(["telesync"])
    plugins.register_user_command(["syncprofile"])

    plugins.register_handler(_on_membership_change, type="membership")

def _telesync_config(bot):
    # immediately halt configuration load if it isn't available
    telesync_config = bot.get_config_option("telesync") or {}
    if "enabled" not in telesync_config  or not telesync_config["enabled"]:
        return False
    return telesync_config

def _telesync_membership_change_message(user_name, user_gplus, group_name, membership_event="left"):
    text = '<a href="{user_gplus}">{uname}</a> {membership_event} <b>({gname})</b>'.format(uname=user_name,
                                                                                           user_gplus=user_gplus,
                                                                                           gname=group_name,
                                                                                           membership_event=membership_event)
    return text

@asyncio.coroutine
def _telesync_is_valid_image_link(url):
    """
    :param url:
    :return: result, file_name
    """
    if ' ' not in url:
        if url.startswith(("http://", "https://")):
            if url.endswith((".jpg", ".jpeg", ".gif", ".gifv", ".webm", ".png", ".mp4")):
                ext = url.split(".")[-1].strip()
                file = url.split("/")[-1].strip().replace(".", "").replace("_", "-")
                return True, "{name}.{ext}".format(name=file, ext=ext)
            else:
                with aiohttp.ClientSession() as session:
                    resp = yield from session.get(url)
                    headers = resp.headers
                    resp.close()
                    if "image" in headers['CONTENT-TYPE']:
                        content_disp = headers['CONTENT-DISPOSITION']
                        content_disp = content_disp.replace("\"", "").split("=")
                        file_ext = content_disp[2].split('.')[1].strip()
                        if file_ext in ("jpg", "jpeg", "gif", "gifv", "webm", "png", "mp4"):
                            file_name = content_disp[1].split("?")[0].strip()
                            return True, "{name}.{ext}".format(name=file_name, ext=file_ext)
    return False, ""


def syncprofile(bot, event, *args):
    """link g+ and telegram profile together

    /bot syncprofile <id> - syncs the g+ profile with the telegram profile, id will be posted on telegram"""

    parameters = list(args)

    ho2tg_dict = bot.memory.get_by_path(['profilesync'])['ho2tg']
    tg2ho_dict = bot.memory.get_by_path(['profilesync'])['tg2ho']

    if len(parameters) > 1:
        yield from bot.coro_send_message(event.conv_id, "Too many arguments")
    elif len(parameters) < 1:
        yield from bot.coro_send_message(event.conv_id, "Too few arguments")
    elif len(parameters) == 1:
        if str(parameters[0]) in ho2tg_dict:
            tg_id = ho2tg_dict[str(parameters[0])]
            user_gplus = 'https://plus.google.com/u/0/{uid}/about'.format(uid=event.user_id.chat_id)
            user_text = '<a href="{user_gplus}">{uname}</a>'.format(uname=event.user.full_name, user_gplus=user_gplus)
            ho_id = parameters[0]
            tg2ho_dict[tg_id] = {'user_gplus': user_gplus, 'user_text': user_text, 'ho_id': ho_id}
            # del ho2tg_dict[str(parameters[0])]
            ho2tg_dict[str(event.user_id.chat_id)] = str(tg_id)
            new_mem = {'tg2ho': tg2ho_dict, 'ho2tg': ho2tg_dict}
            bot.memory.set_by_path(['profilesync'], new_mem)
            yield from bot.coro_send_message(event.conv_id, "Succsesfully set up profile sync.")
        else:
            yield from bot.coro_send_message(event.conv_id,
                                             "You have to execute following command from telegram first:")
            yield from bot.coro_send_message(event.conv_id, "/syncprofile")


def telesync(bot, event, *args):
    """join abitrary hangouts and telegram groups together

    * /bot telesync <telegram chat id> - set sync with telegram group
    * /bot telesync - disable sync and clear sync data from memory"""

    parameters = list(args)
    conv_id = event.conv_id

    memory = bot.memory.get_by_path(['telesync'])
    tg2ho_dict = memory['tg2ho']
    ho2tg_dict = memory['ho2tg']

    if len(parameters) == 0:
        if conv_id in ho2tg_dict:
            tg_chat_id = ho2tg_dict[conv_id]

            del ho2tg_dict[conv_id]
            del tg2ho_dict[tg_chat_id]

            yield from bot.coro_send_message(
                conv_id,
                "telesync removed: {}-{}".format(
                    tg_chat_id, conv_id))
        else:
            logger.info('active telesyncs: {}'.format(memory))
            yield from bot.coro_send_message(
                conv_id,
                "telesync did nothing")

    elif len(parameters) == 1:
        tg_chat_id = parameters[0]

        if conv_id in ho2tg_dict:
            yield from bot.coro_send_message(
                conv_id,
                "telesync already active: {}-{}".format(
                    tg_chat_id, conv_id))
        else:
            tg2ho_dict[tg_chat_id] = conv_id
            ho2tg_dict[conv_id] = tg_chat_id

            yield from bot.coro_send_message(
                conv_id,
                "telesync activated: {}-{}".format(
                    tg_chat_id, conv_id))

    else:
        yield from bot.coro_send_message(conv_id, "too many arguments")

    new_memory = {'ho2tg': ho2tg_dict, 'tg2ho': tg2ho_dict}
    bot.memory.set_by_path(['telesync'], new_memory)
    bot.memory.save()


@asyncio.coroutine
def _on_membership_change(bot, event, command=""):
    config_dict = _telesync_config(bot)

    if 'sync_join_messages' not in config_dict or not config_dict['sync_join_messages']:
        return

    # Generate list of added or removed users
    event_users = [event.conv.get_user(user_id) for user_id
                   in event.conv_event.participant_ids]
    names = ', '.join([user.full_name for user in event_users])

    user_gplus = 'https://plus.google.com/u/0/{uid}/about'.format(uid=event.user_id.chat_id)

    membership_event = "joined" if event.conv_event.type_ == hangups.MembershipChangeType.JOIN else "left"
    text = _telesync_membership_change_message(names, user_gplus, event.conv.name, membership_event)

    ho2tg_dict = bot.memory.get_by_path(['telesync'])['ho2tg']

    if event.conv_id in ho2tg_dict:
        yield from tg_bot.sendMessage(ho2tg_dict[event.conv_id], text, parse_mode='html',
                                      disable_web_page_preview=True)
