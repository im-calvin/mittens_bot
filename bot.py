# bot.py
import os

import discord
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
import re
# from jisho_api.word import Word
# from jisho_api.kanji import Kanji

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
TRANSLATE = os.getenv('TRANSLATE_TOKEN')

client = discord.Client()
translate_client = translate.Client.from_service_account_json(
    'googleapi.json')


@client.event
async def on_ready():
    print("もしもし")


@client.event
async def on_message(message):
    if message.author == client.user:  # base case
        return
    if message.author.bot:  # bot doesn't respond to other bots
        return

    # if jap is detected & the confidence is high
    if translate_client.detect_language(message.content)["language"] == "ja" or translate_client.detect_language(message.content)["language"] == "zh":
        if translate_client.detect_language(message.content)["confidence"] > 0.9:
            transl_msg = translate_client.translate(message.content, "en", "text")[
                "translatedText"]  # transl_msg = translated form of message

            if "@" in transl_msg:
                transl_msg = transl_msg.replace("@ ", "@")
            if transl_msg.startswith("https://"):
                return
            if transl_msg.startswith("<:"):
                return

        # making the emotes format themselves properly!

            if (("<:" in transl_msg and ">" in transl_msg) or ("<a:" in transl_msg)):
                # check if the msg contains an emoji that it cannot use:
                # "indices_open" is the list that contains the index's for the '<' char
                # while True:
                #     index1 = transl_msg.find('<')
                #     index2 = transl_msg.find('>')
                #     transl_msg = transl_msg.replace(
                #         transl_msg[index1:index2], "")
                #     if transl_msg.find('<') > -1:
                #         break
                indices_open = [i.start() for i in re.finditer('<', transl_msg)]
                indices_closed = [i.start() for i in re.finditer('>', transl_msg)]
                # if there's an emote there should be equal number of < and >
                for i in range(len(transl_msg)):  # number of emotes
                    # splicing each emote from transl_msg into a list of str
                    # 'emote_id' is a 'list' of all the 'ids' of the emotes in 'transl_msg'
                    emote_id = [int(s) for s in re.findall(
                        r'\b\d+\b', transl_msg[indices_open[i]:indices_closed[i]])]
                    # 'emote_object' is a 'list' of object type 'emoji' with respective 'emote_id'
                    print(emote_id[i])
                    emote_object = [client.get_emoji(emote_id[i])]
                    if emote_object[i].is_usable() == False:
                        for i in range(len(indices_open)):
                            transl_msg = transl_msg.replace(
                                transl_msg[indices_open[i]:indices_closed[i]], "")
                        # sanitizer function
                        while True:
                            index1 = transl_msg.find('<')
                            index2 = transl_msg.find('>')
                            transl_msg = transl_msg.replace(
                                transl_msg[index1:index2], "")
                            if transl_msg.find('<') > -1:
                                break
                else:
                    transl_msg = transl_msg.replace(": ", ":")
            await message.channel.send(transl_msg)

    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")


client.run(TOKEN)
