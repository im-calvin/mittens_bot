from discord.ext import tasks
import json
from datetime import datetime, timedelta, time
from pytz import timezone
import math
import discord
import re
from disputils import EmbedPaginator, pagination
import time as ttime
import requests
import os
from dotenv import load_dotenv

load_dotenv()

server = os.getenv('server')
token = os.getenv('token')

# gets holo_schedule discord-ready


async def schedule(message, client, fileName):

    r = requests.get(url=server, params={
        "token": token,
        "key": fileName
    })
    holo_schedule = json.loads(r.json()['value'])
    await embedMsg(message, holo_schedule, client)


async def specificSchedule(message, msg, fuzzySearch, lower_member_list, all_members_list, client, holo_dict, fileName):
    user_id = message.author.id
    channel_id = message.channel.id
    r = requests.get(url=server, params={
        "token": token,
        "key": fileName
    })
    holo_schedule = json.loads(r.json()['value'])
    msg = ' '.join(msg[1:]).strip()

    if msg == 'en' or msg == 'id' or msg == 'jp' or msg == 'stars' or msg == 'starsen':
        await regionSchedule(message, msg, holo_dict, client, fileName)
        return

    indexOfMember, possibleMatch = await fuzzySearch(message, msg, lower_member_list)
    if indexOfMember == "bruh what":
        await message.channel.send("Couldn't find the channel you specified.")
        return
    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched
        vtuber_channel = all_members_list[indexOfMember]
        # create list of holo_schedule for specific member
        scheduleList = []
        for i in range(len(holo_schedule)):
            if holo_schedule[i]["member"][0] == vtuber_channel:
                scheduleList.append(holo_schedule[i])
        if scheduleList == []:
            await message.channel.send("**" + vtuber_channel + "** does not have any scheduled streams")
            return
        await embedMsg(message, scheduleList, client)

    else:
        await message.channel.send("Couldn't find the channel you specified.")


async def regionSchedule(message, msg, holo_dict, client, fileName):
    r = requests.get(url=server, params={
        "token": token,
        "key": fileName
    })
    holo_schedule = json.loads(r.json()['value'])

    regionList = holo_dict[msg.upper()]
    scheduleList = []

    for i in range(len(holo_schedule)):
        if holo_schedule[i]["member"][0] in regionList:
            scheduleList.append(holo_schedule[i])
    if scheduleList == []:
        await message.channel.send("holo{} has no scheduled streams".format(msg))
        return
    await embedMsg(message, scheduleList, client)
    return


async def embedMsg(message, hList, client):
    # embedVar = discord.Embed(title="Schedule", color=0xfcc174)
    length = len(hList)
    embeds = []
    if (length == 0):
        await message.channel.send("No history cached <:SAD:950162275682107443>")
        return

    for j in range(math.ceil(length/10)):
        embeds.append(discord.Embed(title="Schedule", color=0xfcc174))
        for i in range(10):
            try:
                i = j*10+i
                # holo_time = hList[i].get("time").split(':')
                # holo_date = hList[i].get("date")
                unix_time = hList[i].get("true_date")
                time_str = "<t:" + str(unix_time) + ">"
                relative_time_str = "<t:" + str(unix_time) + ":R>"
                member_str = hList[i].get("member")[0] + " "
                title_str = hList[i].get("title")
                url = hList[i].get("url")

                for i in range(len(title_str)):
                    m = re.search('【(.+?)】', title_str)
                    if m:
                        title_str = m.group(1)

                if title_str == "":
                    title_str = "Link to the stream"

                # print(unix_time)
                if int(ttime.time()) > unix_time:
                    relative_time_str = "`Now Airing!`"
                    # print(mktime(datetime.now(timezone('UTC')).timetuple()))

                embeds[j].add_field(name='{} / {}'.format(
                    time_str, relative_time_str), value='`{}`: [{}]({})'.format(member_str, title_str, url), inline=False)
            except IndexError:
                break

    paginator = EmbedPaginator(client=client, pages=embeds, control_emojis=pagination.ControlEmojis(
        first=None, last=None, close=None))
    await paginator.run(users=[], channel=message.channel)


async def myschedule(message, client):
    r = requests.get(url=server, params={
        "token": token,
        "key": "profiles.json"
    })
    profiles = json.loads(r.json()['value'])

    r = requests.get(url=server, params={
        "token": token,
        "key": "holo_schedule.json"
    })
    holo_schedule = json.loads(r.json()['value'])

    user_id = message.author.id
    channel_id = message.channel.id
    follow_list = []
    for keys, values in profiles.items():
        for i in range(len(values)):
            try:
                if user_id in values[i].values() and channel_id in values[i].values():
                    follow_list.append(keys)
            except KeyError:
                continue
    personalizedFollow = []
    for i in range(len(holo_schedule)):
        if holo_schedule[i]["member"] in follow_list:
            personalizedFollow.append(holo_schedule[i])

    if personalizedFollow == []:
        await message.channel.send('Your oshi has no scheduled streams <:kiaraangy:987566109790208030>')
        return

    await embedMsg(message, personalizedFollow, client)


async def follow_list(message, fileName, twBool, api):
    r = requests.get(url=server, params={
        "token": token,
        "key": fileName
    })
    profiles = json.loads(r.json()['value'])
    if twBool == "twitter":
        for keys in list(profiles):
            name = api.get_user(user_id=keys).name
            profiles[name] = profiles.pop(keys)

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


async def addchannel(message, msg, fuzzySearch, lower_member_list, all_members_list, duplicate, api):
    user_id = message.author.id
    channel_id = message.channel.id
    msg = ' '.join(msg[1:]).strip()
    if msg == '':
        return

    indexOfMember, possibleMatch = await fuzzySearch(message, msg, lower_member_list)
    if indexOfMember == "bruh what":
        await message.channel.send("Couldn't find the channel you specified.")
        return

    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched

        vtuber_channel = all_members_list[indexOfMember]

        await duplicate(message, 'profiles.json', vtuber_channel, 'add', api)

    else:
        await message.channel.send("Couldn't find the channel you specified.")


async def removechannel(message, msg, fuzzySearch, lower_member_list, all_members_list, duplicate, api):
    msg = ' '.join(msg[1:]).strip()
    if msg == '':
        return

    indexOfMember, possibleMatch = await fuzzySearch(message, msg, lower_member_list)
    if indexOfMember == "bruh what":
        await message.channel.send("Couldn't find the channel you specified.")
        return

    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched
        vtuber_channel = all_members_list[indexOfMember]
        await duplicate(message, 'profiles.json', vtuber_channel, 'remove', api)
    else:
        await message.channel.send("Couldn't find the channel you specified.")

# runs the scraper for holo-schedule


async def removeall(message, msg):
    msg = ' '.join(msg[1:]).strip()

    r = requests.get(url=server, params={
        "token": token,
        "key": "profiles.json"
    })
    profiles = json.loads(r.json()['value'])

    chList = []
    for keys, values in profiles.items():
        for i, dict in enumerate(values):

            if [message.channel.id, message.author.id] == list(dict.values()):
                profiles[keys].pop(i)
                chList.append(str(keys))

    r = requests.post(url=server, data={
        "token": token,
        "key": "profiles.json",
        "value": json.dumps(profiles)
    })

    chStr = '**, **'.join(chList)
    await message.channel.send("Removed **" + chStr + "** from your profile")


@ tasks.loop(minutes=1)
async def now_streaming(client):
    r = requests.get(url=server, params={
        "token": token,
        "key": "holo_schedule.json"
    })
    holo_schedule = json.loads(r.json()['value'])
    r = requests.get(url=server, params={
        "token": token,
        "key": "profiles.json"
    })
    profiles = json.loads(r.json()['value'])

    presentDate = datetime.now()
    now_unix = int(datetime.timestamp(presentDate))
    # you really only have to check the latest 5. iterating through holo_schedule
    for i in range(len(holo_schedule)):
        vtuber_channel = holo_schedule[i].get("member")
        user_list = []  # list of userIDs associated with vtuberCh
        for j in range(len(vtuber_channel)):
            user_list.append(profiles[vtuber_channel[j]])
        userDict = {}
        mention_str = ''

        header_str = "**" + vtuber_channel[0] + "** is now live! \n"
        title_str = holo_schedule[i].get("title")
        url = holo_schedule[i].get("url")

        # holo_time = holo_schedule[i].get("time").split(':')
        # holo_date = holo_schedule[i].get("date")
        # unix time for each schedule
        unix_time = holo_schedule[i].get("true_date")
        if unix_time < now_unix and holo_schedule[i].get("live_pinged") == False:
            holo_schedule[i]["live_pinged"] = True

            try:
                for k in range(len(user_list)):  # users = 1st layer of 2d array
                    idList = []
                    # iterate through user_list
                    for j in range(len(user_list[k])):
                        user_id = (user_list[k][j].get("user_id"))
                        channel_id = int(user_list[k][j].get("channel_id"))
                        # if channel_id in userDict:
                        #     # user_id not in userDict[channel_id]:
                        idList.append(user_id)
                        userDict[channel_id] = idList
                        userDict[channel_id] = list(set(userDict[channel_id]))

            except Exception:  # if arr = [], continue
                continue

            for ch in userDict:
                channel = client.get_channel(id=ch)  # channel obj
                for i in range(len(userDict[ch])):
                    mention_str += "<@" + str(userDict[ch][i]) + "> "

                await channel.send(header_str + title_str + "\n=> " + url + "\n" + mention_str)
    r = requests.post(url=server, data={
        "token": token,
        "key": "holo_schedule.json",
        "value": json.dumps(holo_schedule)
    })


@tasks.loop(minutes=10)
async def botDown(botDownCounter, client):
    channel = await client.fetch_channel("739187928248483860")
    botDownCounter -= 1
    if (botDownCounter == 0):
        await channel.send("<@277908415857295361> UR BOT IS DED")
    await channel.send("meow")
