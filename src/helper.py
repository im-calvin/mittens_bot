import json
import tweepy
import discord
import asyncio
import re
from disputils import EmbedPaginator, pagination

async def fuzzySearch(message, msg, lower_member_list):
    try:
        possibleMatch = next(
            x for x in lower_member_list if msg.lower() in x)
    except StopIteration:
        return "bruh what", None
    # await message.channel.send("Couldn't find the channel you specified.")
    indexOfMember = lower_member_list.index(possibleMatch)

    return indexOfMember, possibleMatch  # indexOfMember


async def duplicate(message, fileName, key, purpose, api):
    user_id = message.author.id
    channel_id = message.channel.id
    try:
        with open(fileName, 'r') as f:
            profiles = json.load(f)
    except json.decoder.JSONDecodeError:  # if empty
        profiles = {}

    key = str(key)

    try:
        user_list = profiles[key]
    except KeyError:  # nobody is following 'key'
        profiles[key] = []
        user_list = []

    list_of_all_values = []

    user_index = next((index for (index, d) in enumerate(
        user_list) if d["user_id"] == user_id and d["channel_id"] == channel_id), None)
    for elem in user_list:
        list_of_all_values.append(list(elem.values()))

    with open(fileName, 'w') as g:

        if [channel_id, user_id] in list_of_all_values:  # already exists in file

            if purpose == 'remove':
                del user_list[user_index]
                profiles[key] = user_list

                json.dump(profiles, g, indent=4)
                if fileName == 'twitter.json':
                    # if profiles[key] == []:

                    try:
                        key = api.get_user(user_id=key).name
                    except tweepy.errors.NotFound:
                        pass
                await message.channel.send("Removed **" + key + "** from your profile")

            if fileName == 'twitter.json':
                try:
                    key = api.get_user(user_id=key).name
                except tweepy.errors.NotFound:
                    pass
            if purpose == 'add':
                json.dump(profiles, g, indent=4)
                await message.channel.send("I appreciate your enthusiasm but you can't follow **" + key + "** twice. \nTry making another account?")
        else:
            if purpose == 'remove':
                json.dump(profiles, g, indent=4)
                if fileName == 'twitter.json':
                    key = api.get_user(user_id=key).name
                await message.channel.send("Unable to remove **" + key + "** from your profile")
                return

            if key in profiles:
                profiles[key].append({
                    "channel_id": channel_id,
                    "user_id": user_id
                })
            else:
                profiles[key] = [{
                    "channel_id": channel_id,
                    "user_id": user_id
                }]
            json.dump(profiles, g, indent=4)
            if fileName == 'twitter.json':
                key = api.get_user(user_id=key).name
            await message.channel.send("Added **" + key + "** to your profile")

async def lyrics(message, msg, genius, client):
    msg = ' '.join(msg[1:]).strip()
    lyrics = []
    songs = genius.search_songs(msg)
    for song in songs['hits']:
        url = song['result']['url']
        song_lyrics = genius.lyrics(song_url=url)
        lyrics.append(song_lyrics)

    emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣",
                     "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    songName = []
    # counter = 1
    embedVar = discord.Embed(title="Which song?", color=0xfcc174)

    try:
        for i in range(len(lyrics)):
            songName.append(lyrics[i].split('Lyrics')[0])
            # x = counter
            embedVar.add_field(name=i, value=songName[i], inline=False)
            # lyrics_str = '\n'.join(songName)
            # counter += 1
    except AttributeError:  # song is not found or song has no lyrics
        await message.channel.send('Song not found')
        return

    sentInput = await message.channel.send(embed=embedVar)
    shortNum = min(len(songName), len(emoji_numbers))
    for i in range(shortNum):
        await sentInput.add_reaction(emoji_numbers[i])

    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in emoji_numbers

    try:
        input = await client.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await message.channel.send('Song selection timed out')
        return

    emoteInput = (input[0].emoji)

    def emoteChanger(emoteInput):
        if emoteInput == "0️⃣":
            return 0
        elif emoteInput == "1️⃣":
            return 1
        elif emoteInput == "2️⃣":
            return 2
        elif emoteInput == "3️⃣":
            return 3
        elif emoteInput == "4️⃣":
            return 4
        elif emoteInput == "5️⃣":
            return 5
        elif emoteInput == "6️⃣":
            return 6
        elif emoteInput == "6️7️⃣":
            return 7
        elif emoteInput == "8️⃣":
            return 8
        elif emoteInput == "9️⃣":
            return 9

    songNum = emoteChanger(emoteInput)

    try:
        sendArr = lyrics[songNum].split('\n\n')
    except IndexError:  # assume no match
        await message.channel.send('Song not found')
        return
    # await embedMsg(message, sendArr, len(sendArr))
    # title_str = '\n'.split(sendArr[0], 1)[0]

    sendArr[len(sendArr)-1] = re.sub("[0-9]*Embed",
                                     "", sendArr[len(sendArr)-1])

    embeds = []

    for i in range(len(sendArr)):
        embeds.append(discord.Embed(title=songName[songNum], color=0xfcc174))
        embeds[i].add_field(name='\u200b', value=sendArr[i])

    paginator = EmbedPaginator(
        client=client, pages=embeds, control_emojis=pagination.ControlEmojis(close=None))
    await paginator.run(users=[], channel=message.channel)

def sanitizer(msg):
    msg = re.sub(r'http\S+', '', msg)  # links
    msg = re.sub(r'<.+>', '', msg)
    return msg.strip()  # emotes

async def exceptions(message, client):
    if message.author == client.user:  # base case
        return "bruh what"
    if message.author.bot:  # bot doesn't respond to other bots
        return "bruh what"
    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")
        return "bruh what"
    if 'dying' in message.content or 'ded' in message.content or 'dead' in message.content or 'accident' in message.content:
        await message.add_reaction('<:respawner:972568754049384478>')
    if message.content == "":  # if msg is empty (ie: image)
        return "bruh what"
    if message.content.startswith("::"):  # for egora
        return "bruh what"
    if message.content.startswith('!'):  # for hobbes
        return "bruh what"
    if message.content == "助けて":
        await message.channel.send("Gasket A")
        return "bruh what"
    return

def time_convert(holo_time, holo_date, timezone, datetime, time, timedelta):  # takes an array in 'xx:xx' format
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
