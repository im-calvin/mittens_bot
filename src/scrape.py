from discord.ext import tasks
import json
from datetime import datetime, timedelta, time
from pytz import timezone


async def firstScrape(argparser, main, nickNameDict, YTClient, time_convert, client):
    args = argparser.parse_args(["--eng", "--all", "--title", "--future"])
    holo_list = main.main(args, holo_list=[])
    args = argparser.parse_args(
        ["--tomorrow", "--eng", "--all", "--title", "--future"])
    holo_list = main.main(args, holo_list)
    # print('firstScrape done!')
    # await refresh_access_token()
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)

    scheduleWithCollabs = collabTitleUpdater(
        nickNameDict, YTClient, holo_schedule)

    # await asyncio.sleep(1.0)
    await new_schedule(time_convert, client)

# scrapes website and then pings user on a rolling basis whenever new holo_schedule comes out


@ tasks.loop(seconds=15*60)
async def get_holo_schedule(argparser, main, nickNameDict, YTClient, time_convert, client):

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
    tomorrow_list = (main.main(args, holo_list=[]))

    try:
        joinedList = today_list + tomorrow_list
    except TypeError:  # if tmr_list is empty
        joinedList = today_list

    scheduleWithCollabs = collabTitleUpdater(
        nickNameDict, YTClient, joinedList)

    list_of_old_url = [dict['url'] for dict in holo_schedule]

    for i in range(len(joinedList)):
        for j in range(len(holo_schedule)):
            joinedList[i]['member'] = scheduleWithCollabs[i]['member']
            # if the new list entry is the exact same as the old list
            if joinedList[i].get("url") in list_of_old_url and holo_schedule[j]["mentioned"] == True:
                joinedList[i]["mentioned"] = True
            # only if live-pinged is true, update the new list for live-pinged to be true
            if holo_schedule[j].get("url") == joinedList[i].get("url") and holo_schedule[j]["live_pinged"] == True:
                joinedList[i]["live_pinged"] = True
    with open('holo_schedule.json', 'w') as f:
        json.dump(joinedList, f, indent=4)

    # print('holo_schedule.json updated')

    # for history
    try:
        with open('history.json', 'r') as f:
            history_dict = json.load(f)
    except Exception:  # if empty
        history_dict = []

    for dictEntry in history_dict:
        holo_date = dictEntry["true_date"]
        tz = timezone("Asia/Tokyo")
        curr_date = int(datetime.now(tz).timestamp())
        if (curr_date - holo_date > 86400):
            history_dict.remove(dictEntry)

    for i in range(len(holo_schedule)):
        if not any(holo_schedule[i]['url'] == dict['url'] for dict in joinedList):
            history_dict.append(holo_schedule[i])

    with open('history.json', 'w') as f:
        json.dump(history_dict, f, indent=4)

    await new_schedule(time_convert, client)


def collabTitleUpdater(nickNameDict, YTClient, holo_schedule):

    for i in range(len(holo_schedule)):
        title_str = holo_schedule[i]['title']
        url = holo_schedule[i]['url']
        index = url.find('=')
        # if yt link (not a joqr/twtv)
        if 'youtube' in holo_schedule[i]['title']:
            id = url[index+1:]
            request = YTClient.videos().list(
                part="snippet",
                id=id)
            response = request.execute()
            try:
                description = response['items'][0]['snippet']['description']
            except IndexError:  # if unarchived stream and time has passed so there is no description
                # holo_schedule[i]['member'].append(keys)

                continue  # break current iteration and continue to next
            # print(description)

            for keys, values in nickNameDict.items():
                for j in range(len(values)):
                    # successfully found matching str
                    if description.find(values[j]) != -1:
                        holo_schedule[i]['member'].append(keys)

    with open('holo_schedule.json', 'w') as f:
        json.dump(holo_schedule, f, indent=4)
    return holo_schedule

# pinging portion


async def new_schedule(time_convert, client):

    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    with open('profiles.json', 'r') as g:
        profiles = json.load(g)

    # list of dicts containing channel_id, user_id
    for i in range(len(holo_schedule)):  # iterate through holo_schedule
        vtuber_channel = holo_schedule[i].get("member")  # list of vTuber names
        user_list = []  # list of userIDs associated with vtuberCh
        for j in range(len(vtuber_channel)):
            user_list.append(profiles[vtuber_channel[j]])
        userDict = {}
        mention_str = ''

        unix_time = holo_schedule[i].get("true_date")
        time_str = "<t:" + str(unix_time) + ">"
        relative_time_str = "<t:" + str(unix_time) + ":R>"
        header_str = "**" + vtuber_channel[0] + "** scheduled a stream at "
        title_str = holo_schedule[i].get("title")
        url = holo_schedule[i].get("url")

        if holo_schedule[i].get("mentioned") == False:
            # set 'mentioned' to true
            holo_schedule[i]["mentioned"] = True
            with open('holo_schedule.json', 'w') as h:
                json.dump(holo_schedule, h, indent=4)
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

                await channel.send('{} {} / {} \n {} \n {}'.format(header_str, time_str, relative_time_str, url, mention_str))
    # print('checking schedule')
