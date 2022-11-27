# bot.py
import os
import re
import discord
import math
from disputils import EmbedPaginator, pagination
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from googleapiclient.discovery import build
import json
import aiohttp
import io
import tweepy
import deepl

from furigana.furigana import print_plaintext
from holo_schedule import main
from discord.ext import commands, tasks
import argparse
import asyncio

from datetime import datetime, timedelta, time
import time as ttime
from time import mktime
from pytz import timezone

from jisho_api.word import Word
from jisho_api.kanji import Kanji
from jisho_api.tokenize import Tokens
from lyricsgenius import Genius

from src.helper import *
from src.msg import *
from src.scrape import *
from src.translator import *
from src.twitter import *

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
TRANSLATE = os.getenv('TRANSLATE_TOKEN')
consumer_key = os.getenv('TWITTER_API')
consumer_secret = os.getenv('TWITTER_API_SECRET')
access_token = os.getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
bearer_token = os.getenv('BEARER_TOKEN')
deepl_token = os.getenv('DEEPL')
genius_client = os.getenv('LYRICS_CLIENT')
genius_secret = os.getenv('LYRICS_SECRET')
YTClientID = os.getenv('YT_CLIENT_ID')
YTClientSecret = os.getenv('YT_CLIENT_SECRET')
refresh_token = os.getenv('YT_REFRESH_TOKEN')

intents = discord.Intents.default()
intents.reactions = True
client = discord.Client(intents=intents)
intents = discord.Intents.all()
TWClient = tweepy.Client(bearer_token)

json_acct_info = json.loads(os.getenv('GOOGLEAPIJSON'))
translate_client = translate.Client.from_service_account_info(
    json_acct_info)
auth = tweepy.OAuth1UserHandler(
    consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)
dlTrans = deepl.Translator(deepl_token)
genius = Genius(genius_client)
YTClient = build('youtube', 'v3', developerKey=TRANSLATE)


all_members_list = []
with open('holo_members.txt', 'rb') as f:
    file_content = f.readlines()[1:]  # Ignore first row
    for member_block in file_content:
        all_members_list.extend(
            member_block.decode("utf-8").split(','))
    # Delete break symbol
    all_members_list[-1] = all_members_list[-1].replace('\n', '')
    for i in range(len(all_members_list)):
        all_members_list[i] = all_members_list[i].replace('\n', '')
        all_members_list[i] = all_members_list[i].replace('\r', '')
        all_members_list[i] = all_members_list[i].replace('*', '')
        all_members_list[i] = all_members_list[i].replace(':', '')
lower_member_list = [x.lower() for x in all_members_list]
PREFIX = "$"
holo_list = []
twDict = {}
global botDownCounter
botDownCounter = 2


# createProfile()
try:
    with open('profiles.json', 'r') as f:
        profiles = json.load(f)
except FileNotFoundError:  # if doesn't exist
    profiles = {}
    for i in all_members_list:
        profiles[i] = []
    with open('profiles.json', 'w') as f:
        json.dump(profiles, f, indent=4)


@client.event
async def on_ready():
    # # これで前のholo_listを確認すると
    # # 前の結果で確認
    # refresh_access_token.start()
    # if not refresh_access_token.is_running():
    #     refresh_access_token.start()  # in case on_ready gets called a 2nd time
    # await refresh_access_token

    await firstScrape(argparser, main, nickNameDict, YTClient, time_convert, client)
    createTweet(api, twDict)

    if not get_holo_schedule.is_running() or not now_streaming.is_running() or not tweetScrape.is_running():
        get_holo_schedule.start(
            argparser, main, nickNameDict, YTClient, time_convert, client)  # background task
        now_streaming.start(time_convert, client)
        tweetScrape.start(TWClient, createTweet, twDict,
                          api, sanitizer, tweepy)
        botDown.start()

    print("もしもし")


message_dict = {}
profiles = {}
user_list = []


@client.event
async def on_message(message):
    translMode = 'google'

    flag = await exceptions(message, client)
    if flag == "bruh what":
        return

    # profiles
    if message.content[0] == PREFIX:
        msg = message.content[1:].split(' ')
        command = msg[0].strip()
        if command == "help":
            await message.channel.send('add, remove, schedule [en, jp, id, stars, \'name\'], myschedule, members, list, twadd, twremove, twlist, transl, kana, lyrics')

        elif command == "add":
            await addchannel(message, msg, TWClient, tweepy, duplicate)

        elif command == "remove":
            await removechannel(message, msg, TWClient, duplicate)

        elif command == "removeall":
            await removeall(message, msg)

        elif command == "schedule" or command == 's':
            try:
                if msg[1] != "":  # if there is anything afterwards
                    await specificSchedule(message, msg, fuzzySearch, lower_member_list, all_members_list, client)

            except IndexError:  # if there's no name
                await schedule(message, client)

        elif command == "myschedule" or command == 'mys':
            await myschedule(message, client)

        elif command == "members":
            await message.channel.send(MEMBER_LIST_STR)

        elif command == "list":
            await follow_list(message, 'profiles.json', 'x', api)

        elif command == "json":
            await message.channel.send(file=discord.File(msg[1]))

        elif command == "twadd":
            await tweetAdd(message, msg)

        elif command == "twlist":
            await follow_list(message, 'twitter.json', 'twitter', api)

        elif command == "twremove":
            await tweetRemove(message, msg, TWClient, duplicate)

        elif command == "transl":
            translMode = await transl(message, msg, translMode="google")

        elif command == "kana":
            await kana(message, print_plaintext)

        elif command == "lyrics":
            await lyrics(message, msg, genius, client)

        elif command == "history":
            await history(message, client)

        else:
            await message.channel.send('Unknown command')

        return

    if translMode == 'deepl':
        transl_msg = deepl_translator(message, dlTrans, sanitizer)
    elif translMode == 'google':
        transl_msg = translator(message, translate_client, sanitizer)
    if transl_msg == "bruh what":
        return
    bot_msg = await message.channel.send(transl_msg, translate_client, sanitizer)
    message_dict[message.id] = bot_msg


@client.event
async def on_message_edit(before, after):

    flag = await exceptions(after)
    if flag == "bruh what":
        return

    transl_msg = deepl_translator(after)
    if transl_msg == "bruh what":  # msg is empty
        return
    channel = after.channel  # channel object

    try:
        bot_msg = message_dict[after.id]
    except KeyError:
        bot_msg = await after.channel.send(transl_msg)
        message_dict[after.id] = bot_msg

    # message object (from user)
    message = await channel.fetch_message(bot_msg.id)
    await message.edit(content=transl_msg)



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


MEMBER_LIST_STR = """
**Hololive:** Tokino Sora, Roboco-san, Sakura Miko, AZKi, Shirakami Fubuki, Natsuiro Matsuri, Yozora Mel, Akai Haato, Aki Rosenthal, Minato Aqua, Yuzuki Choco, Yuzuki Choko Sub, Nakiri Ayame, Murasaki Shion, Oozora Subaru, Ookami Mio, Nekomata Okayu, Inugami Korone, Shiranui Flare, Shirogane Noel, Houshou Marine, Usada Pekora, Uruha Rushia, Hoshimachi Suisei, Amane Kanata, Tsunomaki Watame, Tokoyami Towa, Himemori Luna, Yukihana Lamy, Momosuzu Nene, Sishiro Botan, Omaru Polka, La+ Darknesss, Takane Lui, Hakui Koyori, Sakamata Chloe, Kazama Iroha
**Holostars:** Hanasaki Miyabi, Kanade Izuru, Arurandeisu, Rikka, Astel Leda, Kishidou Tenma, Yukoku Roberu, Kageyama Shien, Aragami Oga, Yatogami Fuma, Utsugi Uyu, Hizaki Gamma, Minase Rio
**HoloID:** Ayunda Risu, Moona Hoshinova, Airani Iofifteen, Kureiji Ollie, Anya Melfissa, Pavolia Reine, Vestia Zeta, Kaela Kovalskia, Kobo Kanaeru
**HoloEN:** Mori Calliope, Takanashi Kiara, Ninomae Ina'nis, Gawr Gura, Watson Amelia, IRyS, Tsukumo Sana, Ceres Fauna, Ouro Kronii, Nanashi Mumei, Hakos Baelz
**Holostars EN:** Syrios, Vesper, Altare, Dezmond
"""

# MEMBER_LIST_STR = all_members_list

# using +1 instead of 0 to remove the titles: 'holoEN, holoID, holostars...'

holoJP = all_members_list[1:all_members_list.index('holostars')]
holoSTARS = all_members_list[all_members_list.index(
    'holostars')+1:all_members_list.index('holoID')]
holoID = all_members_list[all_members_list.index(
    'holoID')+1:all_members_list.index('holoEN')]
holoEN = all_members_list[all_members_list.index('holoEN')+1:]

holo_dict = {
    'JP': holoJP,
    'EN': holoEN,
    'ID': holoID,
    'STARS': holoSTARS
}

nickNameDict = {
    "Gawr Gura": ["@Gawr Gura Ch. hololive-EN", "https://www.youtube.com/channel/UCoSrY_IQQVpmIRZ9Xf-y93g"],
    "Ninomae Ina'nis": ["@Ninomae Ina'nis Ch. hololive-EN", "https://www.youtube.com/channel/UCMwGHR0BTZuLsmjY_NT5Pwg"],
    "Mori Calliope": ["@Mori Calliope Ch. hololive-EN", "https://www.youtube.com/channel/UCL_qhgtOy0dy1Agp8vkySQg"],
    "Watson Amelia": ["@Watson Amelia Ch. hololive-EN", "https://www.youtube.com/channel/UCyl1z3jo3XHR1riLFKG5UAg"],
    "Takanashi Kiara": ["@Takanashi Kiara Ch. hololive-EN", "https://www.youtube.com/channel/UCHsx4Hqa-1ORjQTh9TYDhww"],
    "Nanashi Mumei": ["@Nanashi Mumei Ch. hololive-EN", "https://www.youtube.com/channel/UC3n5uGu18FoCy23ggWWp8tA"],
    "Ceres Fauna": ["@Ceres Fauna Ch. hololive-EN", "https://www.youtube.com/channel/UCO_aKKYxn4tvrqPjcTzZ6EQ"],
    "Ouro Kronii": ["@Ouro Kronii Ch. hololive-EN", "https://www.youtube.com/channel/UCmbs8T6MWqUHP1tIQvSgKrg"],
    "Hakos Baelz": ["@Hakos Baelz Ch. hololive-EN", "https://www.youtube.com/channel/UCgmPnx-EEeOrZSg5Tiw7ZRQ"],
    "IRyS": ["@IRyS Ch. hololive-EN", "https://www.youtube.com/channel/UC8rcEBzJSleTkf_-agPM20g"],
    "Shirakami Fubuki": ["@フブキCh。白上フブキ"],
    "Yuzuki Choco": ["@Choco Ch. 癒月ちょこ"],
    "La+ Darknesss": ["@Laplus ch. ラプラス・ダークネス - holoX -"],
    "Momosuzu Nene": ["@Nene Ch.桃鈴ねね"]
}

client.run(TOKEN)
