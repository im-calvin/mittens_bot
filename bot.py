# bot.py
from array import typecodes
import os
import discord
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
import json

from platformdirs import user_log_dir
from holo_schedule import main
from discord.ext import commands, tasks
import argparse
import json
import asyncio

from datetime import datetime, timedelta, time
from time import mktime
from pytz import timezone

# from jisho_api.word import Word
# from jisho_api.kanji import Kanji

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
TRANSLATE = os.getenv('TRANSLATE_TOKEN')

client = discord.Client()
intents = discord.Intents.all()
translate_client = translate.Client.from_service_account_json(
    'googleapi.json')


all_members_list = []
PREFIX = "$"
holo_list = []


@client.event
async def on_ready():
    # # これで前のholo_listを確認すると
    # # 前の結果で確認
    #
    await firstScrape()
    # must run new_schedule BEFORE get_holo_schedule and AFTER firstScrape
    # new_schedule.start()
    get_holo_schedule.start()  # background task
    now_streaming.start()
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
        f.close()
    print("もしもし")


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
        if command == "help":
            await message.channel.send('add, remove, schedule, members, list')
            return
        if command == "add":
            await addchannel(message, msg)
            return
        if command == "remove":
            await removechannel(message, msg)
            return
        if command == "schedule":
            await schedule(message)
            return
        if command == "members":
            await message.channel.send(MEMBER_LIST_STR)
            return
        if command == "list":
            await follow_list(message)
            return

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
        bot_msg = await after.channel.send(transl_msg)
        message_dict[after.id] = bot_msg

    # message object (from user)
    message = await channel.fetch_message(bot_msg.id)
    await message.edit(content=transl_msg)

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

    if lang == "ja" or lang == "zh-CN" or lang == "zh-TW" or lang == "fr" or lang == "ko" or lang == "zh":
        # zh-TW/HK = taiwan/hongkong, zh-CN = simplified
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
    msg = ' '.join(msg[1:]).strip()
    if msg == '':
        return
    lower_member_list = [x.lower() for x in all_members_list]
    try:
        possibleMatch = next(
            x for x in lower_member_list if msg.lower() in x)
    except StopIteration:
        await message.channel.send("Couldn't find the channel you specified.")
        return
    indexOfMember = lower_member_list.index(possibleMatch)
    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched

        vtuber_channel = all_members_list[indexOfMember]
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
            if user_id in list_of_all_values and channel_id in list_of_all_values:
                json.dump(profiles, g, indent=4)
                await message.channel.send("I appreciate your enthusiasm but you can't follow " + vtuber_channel + " twice. \nTry making another account?")
            else:
                user_list.append(user_info_copy)  # list of user-info
                profiles[vtuber_channel] = user_list
                json.dump(profiles, g, indent=4)
                await message.channel.send("Added " + vtuber_channel + " to your profile")
    else:
        await message.channel.send("Couldn't find the channel you specified.")


async def follow_list(message):
    with open('profiles.json', 'r') as f:
        profiles = json.load(f)
    user_id = message.author.id
    channel_id = message.channel.id
    follow_list = []
    for keys, values in profiles.items():  # iterating through the big dict
        for i in range(len(values)):  # iterating through the array
            try:
                if user_id in values[i].values() and channel_id in values[i].values():
                    follow_list.append(keys)
            except KeyError:
                continue
    follow_list = ', '.join(follow_list)
    header_str = "**You are currently following: \n**"
    await message.channel.send(header_str + follow_list)


async def removechannel(message, msg):
    user_id = message.author.id
    msg = ' '.join(msg[1:]).strip()
    if msg == '':
        return
    lower_member_list = [x.lower() for x in all_members_list]
    try:
        possibleMatch = next(
            x for x in lower_member_list if msg.lower() in x)
    except StopIteration:
        await message.channel.send('couldnt find channel u specified')
        return
    indexOfMember = lower_member_list.index(possibleMatch)
    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched
        vtuber_channel = all_members_list[indexOfMember]
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

# runs the scraper for holo-schedule


async def firstScrape():
    args = argparser.parse_args(["--eng", "--all", "--title", "--future"])
    holo_list = main.main(args, holo_list=[])
    args = argparser.parse_args(
        ["--tomorrow", "--eng", "--all", "--title", "--future"])
    holo_list = main.main(args, holo_list)
    print('firstScrape done!')
    await asyncio.sleep(1.0)
    await new_schedule()

# scrapes website and then pings user on a rolling basis whenever new holo_schedule comes out


@tasks.loop(seconds=15*60)
async def get_holo_schedule():

    # scraping portion
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)

    args = argparser.parse_args(["--eng", "--all", "--title", "--future"])
    # flattenは不正解だけどこんな感じですね
    today_list = (main.main(args, holo_list=[]))

    # this appends

    args = argparser.parse_args(
        ["--tomorrow", "--eng", "--all", "--title", "--future"])
    # flattenは不正解だけどこんな感じですね
    joinedList = (main.main(args, today_list))
####

    # this appends

    list_of_old_url = [dict['url'] for dict in holo_schedule]

    for i in range(len(joinedList)):
        for j in range(len(holo_schedule)):
            # if the new list entry is the exact same as the old list
            if joinedList[i].get("url") in list_of_old_url and holo_schedule[j]["mentioned"] == True:
                joinedList[i]["mentioned"] = True
                # only if live-pinged is true, update the new list for live-pinged to be true
            if holo_schedule[j].get("url") == joinedList[i].get("url") and holo_schedule[j]["live_pinged"] == True:
                joinedList[i]["live_pinged"] = True
            # holo_schedule.append(local_list[i])

    with open('holo_schedule.json', 'w') as f:
        json.dump(joinedList, f, indent=4)

    print('holo_schedule.json updated')

    await new_schedule()
#####
# pinging portion


async def new_schedule():

    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    # holo_schedule = holo_list
    with open('profiles.json', 'r') as g:
        profiles = json.load(g)
        # list of dicts containing channel_id, user_id
    for i in range(len(holo_schedule)):  # iterate through holo_schedule
        vtuber_channel = holo_schedule[i].get("member")
        user_list = profiles.get(vtuber_channel)
        if holo_schedule[i].get("mentioned") == False:
            # set 'mentioned' to true
            holo_schedule[i]["mentioned"] = True
            with open('holo_schedule.json', 'w') as h:
                json.dump(holo_schedule, h, indent=4)
            for j in range(len(user_list)):  # iterate through user_list
                user_id = user_list[j].get("user_id")
                channel_id = int(
                    user_list[j].get("channel_id"))
                channel = client.get_channel(id=channel_id)  # channel obj

                # message send

                holo_time = holo_schedule[i].get("time").split(':')
                holo_date = holo_schedule[i].get("date")
                unix_time = time_convert(holo_time, holo_date)

                time_str = "<t:" + str(unix_time) + ">! \n"
                header_str = vtuber_channel + " scheduled a stream at "
                mention_str = "<@" + str(user_id) + ">\n"
                title_str = holo_schedule[i].get("title")
                url = holo_schedule[i].get("url")
                await channel.send(header_str + time_str + title_str + "\n=> " + url + "\n" + mention_str)
    print('checking schedule')


@tasks.loop(minutes=1)
async def now_streaming():
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    with open('profiles.json', 'r') as g:
        profiles = json.load(g)
    presentDate = datetime.now()
    now_unix = int(datetime.timestamp(presentDate))
    # you really only have to check the latest 5. iterating through holo_schedule
    for i in range(len(holo_schedule)):
        vtuber_channel = holo_schedule[i].get("member")
        user_list = profiles.get(vtuber_channel)
        for j in range((len(user_list))):
            user_id = user_list[j].get("user_id")
            channel_id = int(
                user_list[j].get("channel_id"))
            channel = client.get_channel(
                id=channel_id)  # channel obj

            # message send
            holo_time = holo_schedule[i].get("time").split(':')
            holo_date = holo_schedule[i].get("date")
            # unix time for each schedule
            unix_time = time_convert(holo_time, holo_date)
            # if the time is very close, then the scheduled time - 70 seconds should be less than now_time
            if unix_time < now_unix and holo_schedule[i].get("live_pinged") == False:
                holo_schedule[i]["live_pinged"] = True
                with open('holo_schedule.json', 'w') as f:
                    json.dump(holo_schedule, f, indent=4)
                # time_str = "<t:" + str(unix_time) + ">! \n"
                header_str = vtuber_channel + " is now live! "
                mention_str = "<@" + str(user_id) + ">\n"
                title_str = holo_schedule[i].get("title")
                url = holo_schedule[i].get("url")
                await channel.send(header_str + title_str + "\n=> " + url + "\n" + mention_str)


# converts from jp to unix time


def time_convert(holo_time, holo_date):  # takes an array in 'xx:xx' format
    tz = timezone("Asia/Tokyo")
    now = datetime.now(tz)
    if holo_date == "tomorrow":
        japan_date = now + timedelta(days=1)
    else:
        japan_date = now.date()
    japan_time = time(int(holo_time[0]), int(holo_time[1]))
    japan_dt = tz.localize(
        datetime.combine(japan_date, japan_time))
    unix_time = int(japan_dt.timestamp())
    return unix_time  # returns time in unix format


# gets holo_schedule discord-ready
async def schedule(message):
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    embedVar = discord.Embed(title="Schedule", color=0xfcc174)
    for i in range(10):
        holo_time = holo_schedule[i].get("time").split(':')
        holo_date = holo_schedule[i].get("date")
        unix_time = time_convert(holo_time, holo_date)
        time_str = "<t:" + str(unix_time) + ">"
        member_str = holo_schedule[i].get("member") + " "
        title_str = holo_schedule[i].get("title")
        url = holo_schedule[i].get("url")
        embedVar.add_field(name='{}~ **{}:**'.format(
            time_str, member_str), value='{}'.format(url), inline=False)
    await message.channel.send(embed=embedVar)


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
"""


client.run(TOKEN)
