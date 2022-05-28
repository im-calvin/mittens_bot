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


@client.event
async def on_message(message):

    flag = await exceptions(message)
    if flag == "bruh what":
        return

    # profiles
    if message.content[0] == PREFIX:
        await addchannel(message)

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


@tasks.loop(seconds=5)
async def get_holo_schedule():
    print('bruh what')
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


async def addchannel(message):
    msg = message.content[1:].split(' ')
    command = msg[0]
    user_id = message.author.id
    if command == "addchannel":
        # name of vtuber channel
        try:
            # name of the channel to subscribe to
            vtuber_channel = ' '.join(msg[1:]).strip()
            if vtuber_channel in all_members_list:  # vtuber ch is matched
                profiles[user_id] = {}
                profiles[user_id][vtuber_channel] = 'Subscribed'
                with open('profiles.json', 'w') as f:
                    json.dump(profiles, f, indent=4)
                    f.close()
                await message.channel.send("Added " + vtuber_channel + " to your profile")
            elif vtuber_channel == "":
                await message.channel.send("Please choose a channel to add. You may choose from: \n" + MEMBER_LIST_STR)
            print(vtuber_channel)

        except IndexError:  # if the vtuber_channel is empty
            await message.channel.send("Please choose a channel to add. You may choose from: \n" + MEMBER_LIST_STR)


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
args = argparser.parse_args(["--eng", "--all", "--title"])

MEMBER_LIST_STR = ("**Hololive:** Tokino Sora, Roboco-san, Sakura Miko, AZKi, Shirakami Fubuki, Natsuiro Matsuri, Yozora Mel, Akai Haato, Aki Rose, Minato Aqua, Yuzuki Choco, Yuzuki Choko Sub, Nakiri Ayame, Murasaki Shion, Oozora Subaru, Ookami Mio, Nekomata Okayu, Inugami Korone, Shiranui Flare, Shirogane Noel, Houshou Marine, Usada Pekora, Uruha Rushia, Hoshimatsi Suisei, Amane Kanata, Tsunomaki Watame, Tokoyami Towa, Himemori Luna, Yukihana Lamy, Momosuzu Nene, Sishiro Botan, Omaru Polka, La+ Darknesss, Takane Lui, Hakui Koyori, Sakamata Chloe, Kazama Iroha \n" +
                   "**Holostars:** Hanasaki Miyabi, Kanade Izuru, Arurandeisu, Rikka, Astel Leda, Kishidou Tenma, Yukoku Roberu, Kageyama Shien, Aragami Oga, Yatogami Fuma, Utsugi Uyu, Hizaki Gamma, Minase Rio \n" +
                   "**HoloID:** Risu, Moona, Iofi, Ollie, Anya, Reine, Zeta, Kaela, Kobo \n" +
                   "**HoloEN:** Calli, Kiara, Ina, Gura, Amelia, IRyS, Sana, Fauna, Kronii, Mumei, Baelz")

get_holo_schedule.start()
client.run(TOKEN)
