# gets holo_schedule discord-ready
async def schedule(message, json):
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    await embedMsg(message, holo_schedule)


async def specificSchedule(message, msg, json, fuzzySearch, lower_member_list, all_members_list):
    user_id = message.author.id
    channel_id = message.channel.id
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    msg = ' '.join(msg[1:]).strip()

    if msg == 'en' or msg == 'id' or msg == 'jp' or msg == 'stars':
        await regionSchedule(message, msg)
        return

    indexOfMember, possibleMatch = await fuzzySearch(message, msg)
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
        await embedMsg(message, scheduleList)

    else:
        await message.channel.send("Couldn't find the channel you specified.")


async def regionSchedule(message, msg, json, holo_dict):
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    regionList = holo_dict[msg.upper()]
    scheduleList = []

    for i in range(len(holo_schedule)):
        if holo_schedule[i]["member"][0] in regionList:
            scheduleList.append(holo_schedule[i])
    if scheduleList == []:
        await message.channel.send("holo{} has no scheduled streams".format(msg))
        return
    await embedMsg(message, scheduleList)
    return

async def embedMsg(message, hList, math, discord, time_convert, re, ttime, EmbedPaginator, client, pagination):
    # embedVar = discord.Embed(title="Schedule", color=0xfcc174)
    length = len(hList)
    embeds = []

    for j in range(math.ceil(length/10)):
        embeds.append(discord.Embed(title="Schedule", color=0xfcc174))
        for i in range(10):
            try:
                i = j*10+i
                holo_time = hList[i].get("time").split(':')
                holo_date = hList[i].get("date")
                unix_time = time_convert(holo_time, holo_date)
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

async def myschedule(message, json):
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    with open('profiles.json', 'r') as f:
        profiles = json.load(f)
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

    await embedMsg(message, personalizedFollow)

async def follow_list(message, fileName, twBool, json, api):
    with open(fileName, 'r') as f:
        profiles = json.load(f)
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

    
async def addchannel(message, msg, fuzzySearch, lower_member_list, all_members_list, duplicate):
    user_id = message.author.id
    channel_id = message.channel.id
    msg = ' '.join(msg[1:]).strip()
    if msg == '':
        return

    indexOfMember, possibleMatch = await fuzzySearch(message, msg)
    if indexOfMember == "bruh what":
        await message.channel.send("Couldn't find the channel you specified.")
        return

    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched

        vtuber_channel = all_members_list[indexOfMember]

        await duplicate(message, 'profiles.json', vtuber_channel, 'add')

    else:
        await message.channel.send("Couldn't find the channel you specified.")


async def removechannel(message, msg, fuzzySearch, lower_member_list, all_members_list, duplicate):
    msg = ' '.join(msg[1:]).strip()
    if msg == '':
        return

    indexOfMember, possibleMatch = await fuzzySearch(message, msg)
    if indexOfMember == "bruh what":
        await message.channel.send("Couldn't find the channel you specified.")
        return

    if possibleMatch.lower() in lower_member_list:  # vtuber ch is matched
        vtuber_channel = all_members_list[indexOfMember]
        await duplicate(message, 'profiles.json', vtuber_channel, 'remove')
    else:
        await message.channel.send("Couldn't find the channel you specified.")

# runs the scraper for holo-schedule


async def removeall(message, msg, json):
    msg = ' '.join(msg[1:]).strip()

    with open('profiles.json', 'r') as f:
        profiles = json.load(f)

    chList = []
    for keys, values in profiles.items():
        for i, dict in enumerate(values):

            if [message.channel.id, message.author.id] == list(dict.values()):
                profiles[keys].pop(i)
                chList.append(str(keys))

    with open('profiles.json', 'w') as f:
        json.dump(profiles, f, indent=4)

    chStr = '**, **'.join(chList)
    await message.channel.send("Removed **" + chStr + "** from your profile")
