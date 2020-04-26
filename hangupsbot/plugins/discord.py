'''
Discord sync plugin
By Nick Young

# Installation

Prerequisites:
--------------
Make sure to run pip3 install -r requirements.txt to ensure the Discord modules/dependencies are installed on the hangoutsbot server.

Creating a Discord bot
----------------------
1.  Create a discord App at https://discordapp.com/developers/applications/me#top. 
2.  Enable the "bot user" option - give it an appropriate name.
3.  Take note of the client id on the bot, plus also the Bot token (have to click to reveal the token).  Do not get mixed up with the secret!
4.  Insert the CLIENT ID into this url https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=0
5.  Go to that url to add the bot to the server of your choice - the selection will be dependent upon *your* server access details.
6.  Add the token for the bot to your config with the command /bot config set discord_token "YOUR_TOKEN" (note - you must include the "" around the token)
7.  Restart hangoutsbot
    (note: I had to go into the config.json for the hangout bot and paste it directly into there.  Something was not right via the bot command)
	
Linking the Hangout and Discord channels:
-----------------------------------------
8.  Join the bot to the channel in discord you want to link to HO's.
9.  Say "whereami" in a discord channel that the bot is in and it should respond with the channel id (formated like 123456789123456789)
10. Say "!addrelay CHANNEL_ID" in the hangout you want to sync to the discord channel.

Repeat the last two steps for each discord channel/hangout channel you want to sync.

'''

import asyncio, logging, re

import discord

import plugins

CLIENT = discord.Client()
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

async def send_message_invariant(source, source_id, message):
    """Sends a message to either discord or hangouts"""
    LOGGER.info("Sending message to %s conversation %s: %s", source, source_id, message)
    if source == "discord":
        channel = CLIENT.get_channel(source_id)
        #await CLIENT.send_message(CLIENT.get_channel(source_id), message)
        await channel.send(message)
    elif source == "hangouts":
        await CLIENT.hangouts_bot.coro_send_message(source_id, message)

async def do_help(source, source_id):
    """Send a list of commands back to the sender"""
    help_message = "!addrelay <other_id>, !delrelay <other_id>, !getid, !help"
    await send_message_invariant(source, source_id, help_message)

async def do_getid(source, source_id):
    """Send this conversation's id back to the sender"""
    await send_message_invariant(source, source_id, "This {} channel id: {}".format(source, source_id))

async def do_addrelay(source, source_id, **args):
    """Add a relay from this conversation to the opposite type of conversation"""
    target = "discord" if source == "hangouts" else "hangouts"
    # error: didn't specify target id
    if "arg_string" not in args:
        await send_message_invariant(source, source_id, "usage: !addrelay <{}_id>".format(target))
        return
    arg_string = args["arg_string"]
    target_id = arg_string.split(" ", 1)[0]
    LOGGER.info("relay add request received from %s channel %s to %s channel %s",
                source,
                source_id,
                target,
                target_id)
    relay_map = CLIENT.hangouts_bot.memory.get_by_path(["discord_relay_map"])
    if source_id not in relay_map[source]:
        relay_map[source][source_id] = {}
    if target_id not in relay_map[target]:
        relay_map[target][target_id] = {}
    relay_map[source][source_id][target_id] = True
    relay_map[target][target_id][source_id] = True
    CLIENT.hangouts_bot.memory.set_by_path(["discord_relay_map"], relay_map)
    CLIENT.relay_map = relay_map
    await send_message_invariant(source, source_id, "Relay added to {} channel {}.".format(target, target_id))

async def do_delrelay(source, source_id, **args):
    """Delete a relay"""
    target = "discord" if source == "hangouts" else "hangouts"
    if "arg_string" not in args:
        await send_message_invariant(source, source_id, "usage: !delrelay <{}_id>".format(target))
    arg_string = args["arg_string"]
    target_id = arg_string.split(" ", 1)[0]
    if isinstance(source_id, str):
        source_id = str(source_id)
    LOGGER.info("Relay delete request received from %s channel %s to %s channel %s.",
                source,
                source_id,
                target,
                target_id)
    relay_map = CLIENT.hangouts_bot.memory.get_by_path(["discord_relay_map"])
    if source_id not in relay_map[source]:
        await send_message_invariant(source, source_id, "No relays found for this channel.")
        return
    if target_id not in relay_map[target]:
        await send_message_invariant(source, source_id, "There are no relays to that channel.")
        return
    if target_id not in relay_map[source][source_id] or source_id not in relay_map[target][target_id]:
        msg = "There is no relay between this channel and {} channel {}.".format(target, target_id)
        await send_message_invariant(source, source_id, msg)
        return
    del relay_map[source][source_id][target_id]
    if not relay_map[source][source_id]:
        del relay_map[source][source_id]
    del relay_map[target][target_id][source_id]
    if not relay_map[target][target_id]:
        del relay_map[target][target_id]
    CLIENT.hangouts_bot.memory.set_by_path(["discord_relay_map"], relay_map)
    CLIENT.relay_map = relay_map
    await send_message_invariant(source, source_id, "Relay between {} channel {} and this channel deleted.".format(target, target_id))

async def do_relaydump(source, source_id):
    """Print a list of relay maps"""
    msg = "Here are all of my relays:"
    await send_message_invariant(source, source_id, msg)
    await send_message_invariant(source, source_id, str(CLIENT.relay_map))

COMMAND_DICT = {
    "!help": do_help,
    "!getid": do_getid,
    "!addrelay": do_addrelay,
    "!delrelay": do_delrelay,
    "!relaydump": do_relaydump
}

def _initialize(bot):
    """Hangoutsbot plugin initialization function"""
    plugins.register_handler(_received_message, type="message", priority=50)
    CLIENT.hangouts_bot = bot
    _start_discord_account(bot)
    _init_discord_map(bot)

def _start_discord_account(bot):
    """Log in to discord using token stored in config file"""
    loop = asyncio.get_event_loop()
    LOGGER.info("start discord account here")
    discord_config = bot.get_config_option('discord')
    token = discord_config['token']
    coro = CLIENT.start(token)
    asyncio.run_coroutine_threadsafe(coro, loop)

def _init_discord_map(bot):
    """Creates a relay map if it doesn't exist and reads it into memory"""
    if not bot.memory.exists(["discord_relay_map"]):
        bot.memory.set_by_path(["discord_relay_map"], {})
    relay_map = bot.memory.get_by_path(["discord_relay_map"])
    if "discord" not in relay_map:
        relay_map["discord"] = {}
    if "hangouts" not in relay_map:
        relay_map["hangouts"] = {}
    bot.memory.set_by_path(["discord_relay_map"], relay_map)
    CLIENT.relay_map = relay_map
    LOGGER.info("Generated relay map")
    LOGGER.info(relay_map)

@CLIENT.event
async def on_ready():
    """Discord ready handler"""
    LOGGER.info("Logged in as")
    LOGGER.info(CLIENT.user.name)
    LOGGER.info(CLIENT.user.id)
    LOGGER.info("------")

async def parse_command(source, source_id, content):
    """Parse commands. Supported commands are !getid, !addrelay, !delrelay, !help
    Return True if a command was found"""
    LOGGER.info("content is %s", content)
    tokens = content.split(" ", 1)
    command = tokens[0]
    if command in COMMAND_DICT:
        LOGGER.debug("command is %s", command)
        if len(tokens) == 1:
            await COMMAND_DICT[command](source, source_id)
        else:
            await COMMAND_DICT[command](source, source_id, arg_string=tokens[1])
        return True
    return False

@CLIENT.event
async def on_message(message):
    """Discord message handler"""

    # Prevent message loopback
    if message.author.id == CLIENT.user.id:
        return

    # Only send regular messages
    if message.type != discord.MessageType.default:
        return

    LOGGER.info("message from discord in {}/{} ({})".format(message.channel.guild, message.channel.name, message.channel.id))

    # Don't send commands through the relay
    if await parse_command("discord", message.channel.id, message.clean_content):
        return

    content = message.clean_content
    author = str(message.author).rsplit('#', 1)[0]
    if message.author.nick:
        author = str(message.author.nick)
    new_message = "<b>{}:</b> {}".format(author, content)
    LOGGER.info(re.sub("(<b>)|(</b>)", "", new_message))
    if str(message.channel.id) in CLIENT.relay_map["discord"]:
        sentToChannelIDs = []
        for convid in CLIENT.relay_map["discord"][str(message.channel.id)]:
            if convid in sentToChannelIDs:
                break
            LOGGER.info("sending to {}".format(convid))
            await CLIENT.hangouts_bot.coro_send_message(convid, new_message)
            sentToChannelIDs.append(convid)

def encode_mentions(message, server):
    """Encode mentions so they're not just displayed as plaintext"""
    tokens = ['<@' + server.get_member_named(token[1:]).id + '>'
        if token.startswith('@') and server.get_member_named(token[1:]) 
        else token 
    for token in message.split()]
    return ' '.join(tokens)

def _received_message(bot, event, command):
    """Hangouts message handler"""
    command = yield from parse_command("hangouts", event.conv_id, event.text)
    if command:
        return
    new_message = "**{}**: {}".format(event.user.full_name, event.text)
    LOGGER.info("message from hangouts conversation %s", event.conv_id)
    LOGGER.info(new_message)

    # Send message to discord
    if event.conv_id in CLIENT.relay_map["hangouts"]:
        sentToChannelIDs = []
        for conv_id in CLIENT.relay_map["hangouts"][event.conv_id]:
            try:
                chan = CLIENT.get_channel(int(conv_id))
            except ValueError as ex:
                LOGGER.warn('"%s" cannot be converted to an int for channel ID purposes: %s' % (conv_id, ex))


            if chan is None:
                continue
            if chan in sentToChannelIDs:
                break

            try:
                server = chan.server
            except AttributeError:
                server = None


            # Properly encode mentions
            if server != None:
                new_message = encode_mentions(new_message, server)

            # Only send to text channels, not voice and other
            if chan.type == discord.ChannelType.text:
                LOGGER.info("sending to discord channel {}".format(chan))
                yield from chan.send(new_message)
                sentToChannelIDs.append(chan)
            else:
                LOGGER.warn("{} is not a text channel id".format(chan))
