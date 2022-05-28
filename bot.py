# bot.py
import os

import discord
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
# from googleapiclient.discovery import build
import json
import holo_schedule.main as scraper
from discord.ext import commands, tasks
import argparse
import sys
import time
import asyncio

import sys
import unicodedata
import argparse
import json

from src.fetch_html import *
from src.scraping import *
from src.util import *


# import re

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

argparser = argparse.ArgumentParser(
    description="Hololive schedule scraping tool",
    formatter_class=argparse.RawTextHelpFormatter)
argparser.add_argument(
    "--eng",
    action="store_true",
    default=False,
    help="Make displayed hololive member's name English",
)
argparser.add_argument(
    "--date", action="store_true", default=False, help="Get the current time in JST"
)
argparser.add_argument(
    "--tomorrow",
    action="store_true",
    default=False,
    help="Show tomorrow's schedule list",
)
argparser.add_argument(
    "--all",
    action="store_true",
    default=False,
    help="Show all available live streaming schedule including holostars, etc.",
)
argparser.add_argument(
    "--title",
    action="store_true",
    default=False,
    help="Show schedule with the titles of the streams",
)
argparser.add_argument(
    "--future",
    action="store_true",
    default=False,
    help="Only show streams starting in the future",
)
args = argparser.parse_args(["--eng", "--all", "--title"])


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


@tasks.loop(seconds=3)
async def get_holo_schedule():
    print('bruh what')
    # scraper.main(args)
    main(args)
get_holo_schedule.start()


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
    if msg.startswith("https://"):
        list = msg.split(None, 1)
        return list[1]
    else:  # assume only at end
        list = msg.rsplit(None, 1)
        return list[0]


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
                await message.channel.send("Please choose a channel to add. You may choose from: \n" + member_list_str)
            print(vtuber_channel)

        except IndexError:  # if the vtuber_channel is empty
            await message.channel.send("Please choose a channel to add. You may choose from: \n" + member_list_str)

LABELS = ("Yesterday", "Today", "Tomorrow", "The day after tomorrow")
holo_list = [] * 100


def main(args):

    if args.date:
        show_date()
        sys.exit(0)

    timezone = check_timezone()

    # Fetch html file from https://schedule.hololive.tv/simple
    source_html = fetch_source_html(args.tomorrow)
    time_list, members_list, url_list = scraping(source_html, args.all)

    if args.future and not args.tomorrow:
        hour_list = list(map(lambda x: int(x.split(':')[0]), time_list))
        filter_map = filter_future(hour_list)
    else:
        filter_map = [True] * len(time_list)

    if timezone != 'Asia/Tokyo':
        time_list = timezone_convert(time_list, timezone)
        date_delta = get_date_delta(timezone)
    else:
        date_delta = 0

    if args.tomorrow:
        date_delta += 1

    # All three lists have the same length
    lists_length = len(time_list)

    members_list = list(map(replace_name, members_list))
    hour_list = list(map(lambda x: int(x.split(':')[0]), time_list))

    # Check if date is shifted
    if hour_list != sorted(hour_list):
        shift_index = check_shift(hour_list)
    else:
        shift_index = None

    title_list = []

    if args.title:
        title_list = fetch_title(url_list)

    # Convert member's name into English
    if args.eng:
        members_list = convert_into_en_list(members_list)

    print('     Time      Member            Streaming URL          ({})'.format(timezone))

    for i, (time, member, url) in enumerate(zip(time_list, members_list, url_list)):
        if not filter_map[i]:
            continue

        # # this is only for time zone differences! -- I should implement time zones in my own code.
        if shift_index:
            if shift_index[0] == i - 1:
                print('\n' + LABELS[1+date_delta] + '\n')

            if shift_index[1] == i - 1:
                print('\n' + LABELS[2+date_delta] + '\n')

        # Check character type of member name
        # Contain Japanese
        if unicodedata.east_asian_width(members_list[i][0]) == 'W':
            m_space = ' ' * ((-2 * len(members_list[i]) + 18))

        else:
            m_space = ' ' * ((-1 * len(members_list[i])) + 18)

        # With titles of streams
        if args.title:
            # always going to have args.title in json

            # updating json file:
            try:
                print('{:2d}   {}~    {}{}{}  {}'.format(
                    i+1, time, member, m_space, url, title_list[i]))

                holo_list.append({
                    "time": time,
                    "member": member,
                    "url": url,
                    "title": title_list[i]
                }
                )

                with open('holo_schedule.json', "w") as f:
                    # replace the old json file every 15m -- write only!
                    # exports json file
                    json.dump(holo_list, f, indent=4)

                    f.close()

            # Some emoji cause this error
            except UnicodeEncodeError:
                title_list[i] = remove_emoji(title_list[i])
                print('{:2d}   {}~    {}{}{}  {}'.format(
                    i+1, time, member, m_space, url, title_list[i]))

                holo_list.append({
                    "time": time,
                    "member": member,
                    "url": url,
                    "title": title_list[i]
                }
                )

                with open('holo_schedule.json', "w") as f:
                    # replace the old json file every 15m -- write only!
                    # exports json file
                    json.dump(holo_list, f, indent=4)

                    f.close()

        else:
            print('{:2d}   {}~    {}{}{}'.format(
                i+1, time_list[i], members_list[i], m_space, url_list[i]))
    holo_list = []


member_list_str = ("**Hololive:** Tokino Sora, Roboco-san, Sakura Miko, AZKi, Shirakami Fubuki, Natsuiro Matsuri, Yozora Mel, Akai Haato, Aki Rose, Minato Aqua, Yuzuki Choco, Yuzuki Choko Sub, Nakiri Ayame, Murasaki Shion, Oozora Subaru, Ookami Mio, Nekomata Okayu, Inugami Korone, Shiranui Flare, Shirogane Noel, Houshou Marine, Usada Pekora, Uruha Rushia, Hoshimatsi Suisei, Amane Kanata, Tsunomaki Watame, Tokoyami Towa, Himemori Luna, Yukihana Lamy, Momosuzu Nene, Sishiro Botan, Omaru Polka, La+ Darknesss, Takane Lui, Hakui Koyori, Sakamata Chloe, Kazama Iroha \n" +
                   "**Holostars:** Hanasaki Miyabi, Kanade Izuru, Arurandeisu, Rikka, Astel Leda, Kishidou Tenma, Yukoku Roberu, Kageyama Shien, Aragami Oga, Yatogami Fuma, Utsugi Uyu, Hizaki Gamma, Minase Rio \n" +
                   "**HoloID:** Risu, Moona, Iofi, Ollie, Anya, Reine, Zeta, Kaela, Kobo \n" +
                   "**HoloEN:** Calli, Kiara, Ina, Gura, Amelia, IRyS, Sana, Fauna, Kronii, Mumei, Baelz")

client.run(TOKEN)
