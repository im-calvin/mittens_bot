# bot.py
import os
import re
import discord
import math
from disputils import EmbedPaginator, pagination
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import google
import json
import aiohttp
import io
import tweepy
import deepl

from furigana.furigana import print_plaintext
from holo_schedule import main
from discord.ext import commands, tasks
import argparse
import json
import asyncio

from datetime import datetime, timedelta, time
import time as ttime
from time import mktime
from pytz import timezone

from jisho_api.word import Word
from jisho_api.kanji import Kanji
from jisho_api.tokenize import Tokens
from lyricsgenius import Genius

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
translate_client = translate.Client.from_service_account_json(
    'googleapi.json')
auth = tweepy.OAuth1UserHandler(
    consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)
dlTrans = deepl.Translator(deepl_token)
genius = Genius(genius_client)


def refreshToken(client_id, client_secret, refresh_token):
    params = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }

    authorization_url = "https://oauth2.googleapis.com/token"

    r = requests.post(authorization_url, data=params)

    if r.ok:
        return r.json()['access_token']
    else:
        return None


def generateRefreshToken():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file='yt_client_secret.json', scopes=["https://www.googleapis.com/auth/youtube.readonly"])
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', credentials=credentials)
    request = youtube.channels().list(
        part="snippet",
        id="UC_x5XG1OV2P6uZZ5FSM9Ttw"
    )
    response = request.execute()
    print(response)


# generateRefreshToken()


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


def createTweet():
    global twDict
    try:
        with open('twitter.json', 'r') as f:
            twitter = json.load(f)
        for keys in twitter:
            # twDict dict with keys as twitter IDs and empty value
            # twDict value should be most recent id from x user
            tweets_list = api.user_timeline(
                user_id=keys, count=1, tweet_mode='extended')
            try:
                twDict[keys] = tweets_list[0].id_str
            except IndexError:  # if being run from tweetScrape error and user has no tweets
                twDict[keys] = {}

    except json.decoder.JSONDecodeError:  # if twitter.json empty
        print('twitter.json is empty')
        pass


# createProfile()
try:
    with open('profiles.json', 'r') as f:
        profiles = json.load(f)
except json.decoder.JSONDecodeError:  # if empty
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
    if not refresh_access_token.is_running():
        refresh_access_token.start()  # in case on_ready gets called a 2nd time
    await refresh_access_token()

    await firstScrape()
    createTweet()

    if not get_holo_schedule.is_running() or not now_streaming.is_running() or not tweetScrape.is_running():
        get_holo_schedule.start()  # background task
        now_streaming.start()
        tweetScrape.start()

    print("もしもし")


message_dict = {}
profiles = {}
user_list = []


@client.event
async def on_message(message):
    translMode = 'google'

    flag = await exceptions(message)
    if flag == "bruh what":
        return

    # profiles
    if message.content[0] == PREFIX:
        msg = message.content[1:].split(' ')
        command = msg[0].strip()
        if command == "help":
            await message.channel.send('add, remove, schedule [en, jp, id, stars, \'name\'], myschedule, members, list, twadd, twremove, twlist, transl, kana')

        elif command == "add":
            await addchannel(message, msg)

        elif command == "remove":
            await removechannel(message, msg)

        elif command == "removeall":
            await removeall(message, msg)

        elif command == "schedule" or command == 's':
            try:
                if msg[1] != "":  # if there is anything afterwards
                    await specificSchedule(message, msg)

            except IndexError:  # if there's no name
                await schedule(message)

        elif command == "myschedule" or command == 'mys':
            await myschedule(message)

        elif command == "members":
            await message.channel.send(MEMBER_LIST_STR)

        elif command == "list":
            await follow_list(message, 'profiles.json', 'x')

        elif command == "json":
            await message.channel.send(file=discord.File(msg[1]))

        elif command == "twadd":
            await tweetAdd(message, msg)

        elif command == "twlist":
            await follow_list(message, 'twitter.json', 'twitter')

        elif command == "twremove":
            await tweetRemove(message, msg)

        elif command == "transl":
            translMode = await transl(message, msg, translMode="google")

        elif command == "kana":
            await kana(message)

        elif command == "lyrics":
            await lyrics(message, msg)

        else:
            await message.channel.send('Unknown command')

        return

    if translMode == 'deepl':
        transl_msg = deepl_translator(message)
    elif translMode == 'google':
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


async def lyrics(message, msg):
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


# twitter follow


async def tweetAdd(message, msg):
    vtuber_channel = ' '.join(msg[1:]).strip()
    if vtuber_channel == '':
        return

    try:
        response = TWClient.get_user(username=vtuber_channel)
    except tweepy.errors.BadRequest:
        await message.channel.send('Twitter user not found. Make sure that you inputted the right twitter handle. \nExample: @gawrgura would be \"gawrgura\"')
        return
    id = response.data.id

    await duplicate(message, 'twitter.json', id, 'add')


async def tweetRemove(message, msg):
    vtuber_channel = ' '.join(msg[1:]).strip()
    if vtuber_channel == '':
        return

    response = TWClient.get_user(username=vtuber_channel)
    id = response.data.id

    await duplicate(message, 'twitter.json', id, 'remove')


@tasks.loop(seconds=60)
async def tweetScrape():
    try:
        try:
            with open('twitter.json', 'r') as f:
                twitter = json.load(f)
        except json.decoder.JSONDecodeError:  # if twitter.json is empty
            return

        for keys, values in twitter.items():  # iterating over the json file
            # test = False
            userDict = {}  # '2d array', k = channel_id, v = arr of user_ids
            mention_str = ''
            noPic = False
            isRef = False

            try:
                tweets_list = TWClient.get_users_tweets(id=keys, expansions=[
                                                        "attachments.media_keys", "referenced_tweets.id", "author_id"], since_id=twDict[keys])
            except KeyError:  # if twitter user was added while the bot was running
                # THIS ERROR ISN'T FIXED
                createTweet()
                return

            # debugging line:
            # tweets_list = TWClient.get_users_tweets(id=keys, expansions=[
            #     "attachments.media_keys", "referenced_tweets.id", "author_id"])

            if tweets_list.data != None:
                # if tweets_list.data == None:
                tweetID_list = tweets_list.data
                twDict[keys] = tweetID_list[0].id
                # in case more than one tweet within 30s
                for i in reversed(range(len(tweetID_list))):
                    userDict = {}
                    mention_str = ''
                    noPic = False
                    tweetTxt = ''

                    tweetID = tweetID_list[i].id

                    username = api.get_user(user_id=keys).name
                    name = api.get_user(user_id=keys).screen_name
                    tweetObj = TWClient.get_tweet(
                        id=tweetID, expansions=['attachments.media_keys', 'referenced_tweets.id', 'author_id'], media_fields=['preview_image_url'])
                    apiObj = api.get_status(id=tweetID, tweet_mode='extended')

                    header_str = f"**{username}** just tweeted! \n"

                    try:  # if it's a retweet
                        apiObj = apiObj.retweeted_status
                        RTname = api.get_user(user_id=apiObj.user.id_str).name
                        header_str = f"**{username}** just retweeted **{RTname}**\n"
                        # header_str = "**" + username + "** just retweeted " + api.get_user(user_id=apiObj.id_str).name + '\n'
                    except AttributeError:  # if not a retweet
                        pass
                    try:  # if it's a reply
                        refTweet = tweetObj.data.referenced_tweets
                        if refTweet[0].type == 'replied_to':
                            ogtweetID = refTweet[0].id
                            ogTwObj = TWClient.get_tweet(  # original tweet object
                                id=ogtweetID, expansions=['attachments.media_keys', 'referenced_tweets.id', 'author_id'], media_fields=['preview_image_url'])
                            replyName = ogTwObj.includes['users'][0].name
                            ogAPIObj = api.get_status(
                                id=ogtweetID, tweet_mode='extended')
                            header_str = f"**{username}** just replied to **{replyName}**!\n"
                            tweetTxt = sanitizer(ogAPIObj.full_text).strip()
                            isRef = True
                            await sendTweetMsg(ogAPIObj, header_str, mention_str, noPic, isRef, keys, values, tweetTxt, name, tweetID)
                            header_str = ''
                            mention_str = ''
                            userDict = {}
                            isRef = False
                    except TypeError:
                        pass

                    tweetID = apiObj.id_str

                    tweetTxt = sanitizer(apiObj.full_text).strip()
                    # tweetObj = TWClient.get_tweet(
                    #     id=tweetID, expansions=['attachments.media_keys', 'referenced_tweets.id'], media_fields=['preview_image_url'])
                    # apiObj = api.get_status(id=tweetID, tweet_mode='extended')

                    # print(apiObj.retweeted)

                    # if there is any media in the tweet
                    # mention_str = ''
                    await sendTweetMsg(apiObj, header_str, mention_str, noPic, isRef, keys, values, tweetTxt, name, tweetID)

    except tweepy.errors.TweepyException:
        print('twitter is overloaded')
        tweetScrape.change_interval(minutes=2)
        return


async def sendTweetMsg(apiObj, header_str, mention_str, noPic, isRef, keys, values, tweetTxt, name, tweetID):
    userDict = {}

    try:
        apiObj.entities['media']
        try:  # if multiple images
            tweetPic = apiObj.extended_entities['media'][0]['media_url_https']
            tweetURL = '<' + \
                apiObj.extended_entities['media'][0]['url'] + '>'
        # if extended_entities doesn't exists (1 img)
        except AttributeError:
            tweetPic = ''
            tweetURL = '<' + \
                apiObj.entities['urls'][1]['url'] + '>'
    except KeyError:  # if no entities
        try:
            tweetURL = apiObj.entities['urls'][0]['url']
            tweetURL = f"\n<{tweetURL}>"
            noPic = True
        except IndexError:  # if ONLY text
            tweetURL = f"\n<https://twitter.com/{name}/status/{tweetID}>"
            noPic = True

    # print(tweetPic)
    # print(tweetURL)

    # reading tweetPic url and converting to file object
    if noPic == False:
        async with aiohttp.ClientSession() as session:
            async with session.get(tweetPic) as resp:
                if resp.status != 200:
                    noPic = True
                data = io.BytesIO(await resp.read())

    # if now < tweetTime:  # should be <

        # sending to multiple channels
    try:
        for j in range(len(values)):  # iterate through user_list
            user_id = (values[j].get("user_id"))
            channel_id = int(values[j].get("channel_id"))

            if channel_id in userDict:
                userDict[channel_id].append(user_id)
            else:
                userDict[channel_id] = [user_id]
    except TypeError:  # if arr = [], continue
        pass

# print(noPic)
    for ch in userDict:
        channel = client.get_channel(id=ch)
        for i in range(len(userDict[ch])):
            mention_str += "<@" + \
                str(userDict[ch][i]) + "> "
        if noPic == True:
            if isRef == True:
                await channel.send(content=header_str + tweetTxt + '\n')
                return
            await channel.send(content=header_str + tweetTxt + tweetURL + '\n' + mention_str)
        else:
            if isRef == True:
                await channel.send(content=header_str + tweetTxt + '\n', file=discord.File(data, 'img.jpg'))
                return
            await channel.send(content=header_str + tweetTxt + '\n' + tweetURL + '\n' + mention_str, file=discord.File(data, 'img.jpg'))

# exceptions for on_message


async def exceptions(message):
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

# sanitize messages


def sanitizer(msg):
    msg = re.sub(r'http\S+', '', msg)  # links
    msg = re.sub(r'<.+>', '', msg)
    return msg.strip()  # emotes


def translator(message):
    lang = translate_client.detect_language(message.content)["language"]
    san_msg = sanitizer(message.content)

    if lang == "ja" or lang == "zh-CN" or lang == "zh-TW" or lang == "fr" or lang == "zh":
        # zh-TW/HK = taiwan/hongkong, zh-CN = simplified
        if translate_client.detect_language(san_msg)["confidence"] > 0.90:
            transl_msg = translate_client.translate(san_msg, "en", "text")[
                "translatedText"]  # transl_msg = translated form of message

            if "@" in transl_msg:
                transl_msg = transl_msg.replace("@ ", "@")

            return transl_msg
        else:
            return "bruh what"
    else:
        return "bruh what"


def deepl_translator(message):
    lang = dlTrans.translate_text(
        message.content, target_lang='en-gb').detected_source_lang

    san_msg = sanitizer(message.content)

    if lang == 'JA' or lang == "FR" or lang == 'KO' or lang == 'ZH' or lang == 'ES' or lang == 'TL':
        try:
            transl_msg = dlTrans.translate_text(
                san_msg, target_lang='en-gb', preserve_formatting=True)
            return transl_msg
        except ValueError:
            return "bruh what"
    else:
        return "bruh what"


async def transl(message, msg, translMode):  # translmode

    msg = ' '.join(msg[1:]).strip()
    if msg == 'deepl':
        translMode = 'deepl'
        await message.channel.send('Translation client set to deepl')
        return translMode
        # return 'deepl'
    elif msg == 'google':
        translMode = 'google'
        await message.channel.send('Translation client set to google')
        return translMode
        # return 'google'
    else:
        await message.channel.send('Choose either \'deepl\' or \'google\'')

# message = message obj, msg = whole msg str, command = msg[1:]


async def kana(message):
    channel = message.channel
    try:
        messageID = message.reference.message_id
    except AttributeError:  # if no reply
        await message.channel.send('You need to reply to a message')
        return

    message = await channel.fetch_message(messageID)
    # r = Tokens.request(message.content)
    # tList = []
    # wordList = []
    # outList = []
    # try:
    #     for i in range(len(r.data)):
    #         tList.append(r.data[i].token)
    #         # try:
    #         wordList.append(Word.request(tList[i]))
    #         outList.append(wordList[i].data[0].japanese[0].reading)
    #         print(wordList[0])
    #     # except:  # if token is not kanji, continue
    #     # pass
    # except AttributeError:  # too short to be multiple phrases (1 phrase)
    #     r = Word.request(message.content)
    #     outList.append(r.data[0].japanese[0].reading)
    #     print(r.data[0])

    # await channel.send(tList)
    # await channel.send(outList)
    # # print(wordList[0].data[0].japanese[0].reading)
    # # print(wordList[[0].data.meta.readings.japanese[0]])
    # # print(xList)

    # print(tList)

    kanaMsg = print_plaintext(message.content)

    await channel.send(kanaMsg)


async def fuzzySearch(message, msg):
    try:
        possibleMatch = next(
            x for x in lower_member_list if msg.lower() in x)
    except StopIteration:
        return "bruh what", None
    # await message.channel.send("Couldn't find the channel you specified.")
    indexOfMember = lower_member_list.index(possibleMatch)

    return indexOfMember, possibleMatch  # indexOfMember


async def duplicate(message, fileName, key, purpose):
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


async def addchannel(message, msg):
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


async def removechannel(message, msg):
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


async def removeall(message, msg):
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


async def firstScrape():
    args = argparser.parse_args(["--eng", "--all", "--title", "--future"])
    holo_list = main.main(args, holo_list=[])
    args = argparser.parse_args(
        ["--tomorrow", "--eng", "--all", "--title", "--future"])
    holo_list = main.main(args, holo_list)
    # print('firstScrape done!')
    # await refresh_access_token()

    scheduleWithCollabs = collabTitleUpdater()

    # await asyncio.sleep(1.0)
    await new_schedule()

# scrapes website and then pings user on a rolling basis whenever new holo_schedule comes out


@ tasks.loop(seconds=15*60)
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
    tomorrow_list = (main.main(args, holo_list=[]))

    try:
        joinedList = today_list + tomorrow_list
    except TypeError:  # if tmr_list is empty
        joinedList = today_list

    with open('holo_schedule.json', 'w') as f:
        json.dump(joinedList, f, indent=4)

    scheduleWithCollabs = collabTitleUpdater()

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

    await new_schedule()


@tasks.loop(minutes=45)
async def refresh_access_token():
    global YTClient
    # // Call refreshToken which creates a new Access Token
    access_token = refreshToken(YTClientID, YTClientSecret, refresh_token)

    # // Pass the new Access Token to Credentials() to create new credentials
    credentials = google.oauth2.credentials.Credentials(access_token)
    YTClient = googleapiclient.discovery.build(
        'youtube', 'v3', credentials=credentials)


def collabTitleUpdater():

    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    for i in range(len(holo_schedule)):
        title_str = holo_schedule[i]['title']
        url = holo_schedule[i]['url']
        index = url.find('=')
        if index != -1:  # if yt link (not a joqr)
            id = url[index+1:]
            request = YTClient.videos().list(
                part="snippet",
                id=id)
            response = request.execute()
            description = response['items'][0]['snippet']['description']
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


async def new_schedule():

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

        holo_time = holo_schedule[i].get("time").split(':')
        holo_date = holo_schedule[i].get("date")
        unix_time = time_convert(holo_time, holo_date)
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


@ tasks.loop(minutes=1)
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
        user_list = []  # list of userIDs associated with vtuberCh
        for j in range(len(vtuber_channel)):
            user_list.append(profiles[vtuber_channel[j]])
        userDict = {}
        mention_str = ''

        header_str = "**" + vtuber_channel[0] + "** is now live! \n"
        title_str = holo_schedule[i].get("title")
        url = holo_schedule[i].get("url")

        holo_time = holo_schedule[i].get("time").split(':')
        holo_date = holo_schedule[i].get("date")
        # unix time for each schedule
        unix_time = time_convert(holo_time, holo_date)
        if unix_time < now_unix and holo_schedule[i].get("live_pinged") == False:
            holo_schedule[i]["live_pinged"] = True
            with open('holo_schedule.json', 'w') as f:
                json.dump(holo_schedule, f, indent=4)

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


async def follow_list(message, fileName, twBool):
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


async def myschedule(message):
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


# gets holo_schedule discord-ready
async def schedule(message):
    with open('holo_schedule.json', 'r') as f:
        holo_schedule = json.load(f)
    await embedMsg(message, holo_schedule)


async def specificSchedule(message, msg):
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


async def regionSchedule(message, msg):
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

bot = commands.Bot(command_prefix='$')


async def embedMsg(message, hList):
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
