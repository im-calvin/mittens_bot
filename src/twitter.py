
import json
import discord
from discord.ext import tasks
import aiohttp
import io
import requests

import os
from dotenv import load_dotenv

load_dotenv()

server = os.getenv('server')
token = os.getenv('token')


async def tweetAdd(message, msg, TWClient, tweepy, duplicate, api):
    vtuber_channel = ' '.join(msg[1:]).strip()
    if vtuber_channel == '':
        return

    try:
        response = TWClient.get_user(username=vtuber_channel)
    except tweepy.errors.BadRequest:
        await message.channel.send('Twitter user not found. Make sure that you inputted the right twitter handle. \nExample: @gawrgura would be \"gawrgura\"')
        return
    id = response.data.id

    await duplicate(message, 'twitter.json', id, 'add', api)


async def tweetRemove(message, msg, TWClient, duplicate, api):
    vtuber_channel = ' '.join(msg[1:]).strip()
    if vtuber_channel == '':
        return

    response = TWClient.get_user(username=vtuber_channel)
    id = response.data.id

    await duplicate(message, 'twitter.json', id, 'remove', api)


@tasks.loop(seconds=60)
async def tweetScrape(TWClient, createTweet, twDict, api, sanitizer, tweepy, client):
    try:
        r = requests.get(url=server, params={
            "token": token,
            "key": "twitter.json"
        })
        if (r.json()['value'] == None):
            return
        twitter = json.loads(r.json()['value'])

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
                createTweet(api)
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
                            await sendTweetMsg(ogAPIObj, header_str, mention_str, noPic, isRef, keys, values, tweetTxt, name, tweetID, client)
                            header_str = ''
                            mention_str = ''
                            userDict = {}
                            isRef = False
                    except TypeError:
                        pass

                    tweetID = apiObj.id_str

                    tweetTxt = sanitizer(apiObj.full_text).strip()

                    await sendTweetMsg(apiObj, header_str, mention_str, noPic, isRef, keys, values, tweetTxt, name, tweetID, client)

    except tweepy.errors.TweepyException:
        print('twitter is overloaded')
        tweetScrape.change_interval(minutes=2)
        return


async def sendTweetMsg(apiObj, header_str, mention_str, noPic, isRef, keys, values, tweetTxt, name, tweetID, client):
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


def createTweet(api):
    global twDict
    r = requests.get(url=server, params={
        "token": token,
        "key": "twitter.json"
    })
    if (r.json()['value']):
        return
    twitter = json.loads(r.json()['value'])

    for keys in twitter:
        # twDict dict with keys as twitter IDs and empty value
        # twDict value should be most recent id from x user
        tweets_list = api.user_timeline(
            user_id=keys, count=1, tweet_mode='extended')
        try:
            twDict[keys] = tweets_list[0].id_str
        except IndexError:  # if being run from tweetScrape error and user has no tweets
            twDict[keys] = {}
