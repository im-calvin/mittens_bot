# bot.py
import os
import discord
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
import json
from holo_schedule import main
from discord.ext import commands, tasks
import argparse
import json

# from jisho_api.word import Word
# from jisho_api.kanji import Kanji

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
TRANSLATE = os.getenv('TRANSLATE_TOKEN')

client = discord.Client()
translate_client = translate.Client.from_service_account_json(
    'googleapi.json')

all_members_list = []
PREFIX = "$"


@client.event
async def on_ready():
    print("もしもし")

    with open('holo_members.txt', 'rb') as f:
        file_content = f.readlines()[1:]  # Ignore first row
        for member_block in file_content:
            all_members_list.extend(
                member_block.decode("utf-8").split(','))
        # Delete break symbol
        all_members_list[-1] = all_members_list[-1].replace('\n', '')
        f.close()

message_dict = {}
profiles = {}
user_list = []


@client.event
async def on_message(message):

    flag = await exceptions(message)
    if flag == "bruh what":
        return

    # profiles
    if message.content[0] == PREFIX:
        msg = message.content[1:].split(' ')
        command = msg[0]
        if command == "addchannel":
            await addchannel(message, msg)
        if command == "removechannel":
            await removechannel(message, msg)

    # translate
    transl_msg = translator(message)
    if transl_msg == "bruh what":
        return
    bot_msg = await message.channel.send(transl_msg)
    message_dict[message.id] = bot_msg


@client.event
async def on_message_edit(before, after):

    flag = await exceptions(after)
    if flag == "bruh what":
        return

    transl_msg = translator(after)
    if transl_msg == "bruh what":  # msg is empty
        return
    channel = after.channel  # channel object

    try:
        bot_msg = message_dict[after.id]
    except KeyError:
        bot_msg = await message.channel.send(transl_msg)
        message_dict[message.id] = bot_msg

    # message object (from user)
    message = await channel.fetch_message(bot_msg.id)
    await message.edit(content=transl_msg)

# runs the scraper for holo-schedule


@tasks.loop(seconds=15*60)
async def get_holo_schedule():
    args = argparser.parse_args(["--eng", "--all", "--title", "--future"])
    main.main(args)
    args = argparser.parse_args(
        ["--tomorrow", "--eng", "--all", "--title", "--future"])
    main.main(args)

# exceptions for on_message


async def exceptions(message):
    if message.author == client.user:  # base case
        return "bruh what"
    if message.author.bot:  # bot doesn't respond to other bots
        return "bruh what"
    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")
    if 'dying' in message.content or 'ded' in message.content or 'dead' in message.content:
        await message.add_reaction('<:respawner:972568754049384478>')
    if message.content == "":  # if msg is empty (ie: image)
        return "bruh what"
    return

# sanitize messages


def sanitizer(msg):
    while True:
        # since slicing is exclusive of index1, inclusive of index2
        index1 = msg.find('<')
        index2 = msg.find('>') + 1
        msg = msg.replace(
            msg[index1:index2], "")
        if msg.find('<') == -1:
            return msg

# sanitize links


def sanitizer_links(msg):  # msg is str
    try:
        if msg.startswith("https://"):
            list = msg.split(None, 1)
            return list[1]
        else:  # assume only at end
            list = msg.rsplit(None, 1)
            return list[0]
    except IndexError:  # only link no msg
        msg = ""


def translator(message):
    lang = translate_client.detect_language(message.content)["language"]
    san_msg = message.content
    if ("<:" in message.content and ">" in message.content):
        san_msg = sanitizer(message.content)  # sanitized msg
    if "https://" in message.content:
        san_msg = sanitizer_links(message.content)

    if lang == "ja" or lang == "zh-CN" or lang == "zh-TW" or lang == "fr" or lang == "ko":
        # zh-TW = traditional, zh-CN = simplified
        if translate_client.detect_language(san_msg)["confidence"] > 0.80:
            transl_msg = translate_client.translate(san_msg, "en", "text")[
                "translatedText"]  # transl_msg = translated form of message

            if "@" in transl_msg:
                transl_msg = transl_msg.replace("@ ", "@")

            return transl_msg
        else:
            return "bruh what"
    else:
        return "bruh what"


# message = message obj, msg = whole msg str, command = msg[1:]
async def addchannel(message, msg):
    user_id = message.author.id
    channel_id = message.channel.id
    vtuber_channel = ' '.join(msg[1:]).strip()  # name of vtuber channel
    if vtuber_channel in all_members_list:  # vtuber ch is matched
        with open('profiles.json', 'r') as f:
            profiles = json.load(f)
        with open('profiles.json', 'w') as g:
            user_info = {  # dict
                "channel_id": channel_id,
                "user_id": user_id
            }
            user_info_copy = user_info.copy()
            user_list = profiles[vtuber_channel]
            list_of_all_values = [
                value for elem in user_list for value in elem.values()]
            # check if User-id is already in
            if user_id in list_of_all_values:
                json.dump(profiles, g, indent=4)
                await message.channel.send("I appreciate your enthusiasm but you can't follow " + vtuber_channel + " twice. \nTry making another account?")
            else:
                user_list.append(user_info_copy)  # list of user-info
                profiles[vtuber_channel] = user_list
                json.dump(profiles, g, indent=4)
                await message.channel.send("Added " + vtuber_channel + " to your profile")
    else:
        await message.channel.send("Please choose a channel. You may choose from: \n" + MEMBER_LIST_STR)


async def removechannel(message, msg):
    user_id = message.author.id
    channel_id = message.channel.id
    vtuber_channel = ' '.join(msg[1:]).strip()  # name of vtuber channel
    if vtuber_channel in all_members_list:
        with open('profiles.json', 'r') as f:
            profiles = json.load(f)
        with open('profiles.json', 'w') as g:
            user_list = profiles[vtuber_channel]
            user_index = next((index for (index, d) in enumerate(
                user_list) if d["user_id"] == user_id), None)
            list_of_all_values = [
                value for elem in user_list for value in elem.values()]
            if user_id in list_of_all_values:
                del user_list[user_index]
                profiles[vtuber_channel] = user_list
                json.dump(profiles, g, indent=4)
                await message.channel.send("Removed " + vtuber_channel + " from your profile")
            else:
                json.dump(profiles, g, indent=4)
                await message.channel.send("Unable to remove " + vtuber_channel + " from your profile")
    else:
        await message.channel.send("Channel not found.")


# @tasks.loop
# async def ping(message):
#     with open('holo_schedule.json', 'r') as f:
#         profiles[]


# code borrowed from https://github.com/TBNV999/holo-schedule-CLI
argparser = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter)
argparser.add_argument(
    "--eng", action="store_true", default=False
)
argparser.add_argument(
    "--date", action="store_true", default=False
)
argparser.add_argument(
    "--tomorrow", action="store_true", default=False
)
argparser.add_argument(
    "--all", action="store_true", default=False
)
argparser.add_argument(
    "--title", action="store_true", default=False
)
argparser.add_argument(
    "--future", action="store_true", default=False
)


MEMBER_LIST_STR = ("**Hololive:** Tokino Sora, Roboco-san, Sakura Miko, AZKi, Shirakami Fubuki, Natsuiro Matsuri, Yozora Mel, Akai Haato, Aki Rose, Minato Aqua, Yuzuki Choco, Yuzuki Choko Sub, Nakiri Ayame, Murasaki Shion, Oozora Subaru, Ookami Mio, Nekomata Okayu, Inugami Korone, Shiranui Flare, Shirogane Noel, Houshou Marine, Usada Pekora, Uruha Rushia, Hoshimatsi Suisei, Amane Kanata, Tsunomaki Watame, Tokoyami Towa, Himemori Luna, Yukihana Lamy, Momosuzu Nene, Sishiro Botan, Omaru Polka, La+ Darknesss, Takane Lui, Hakui Koyori, Sakamata Chloe, Kazama Iroha \n" +
                   "**Holostars:** Hanasaki Miyabi, Kanade Izuru, Arurandeisu, Rikka, Astel Leda, Kishidou Tenma, Yukoku Roberu, Kageyama Shien, Aragami Oga, Yatogami Fuma, Utsugi Uyu, Hizaki Gamma, Minase Rio \n" +
                   "**HoloID:** Risu, Moona, Iofi, Ollie, Anya, Reine, Zeta, Kaela, Kobo \n" +
                   "**HoloEN:** Calli, Kiara, Ina, Gura, Amelia, IRyS, Sana, Fauna, Kronii, Mumei, Baelz")

get_holo_schedule.start()
client.run(TOKEN)
