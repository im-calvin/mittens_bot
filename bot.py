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
async def on_message(message):
    if message.author == client.user:  # base case
        return
    # if jap is detected & the confidence is high
    if translate_client.detect_language(message.content)["language"] == "ja" and translate_client.detect_language(message.content)["confidence"] > 0.95:
        transl_msg = translate_client.translate(message.content, "en", "text")[
            "translatedText"]  # transl_msg = translated form of message
        # if the message contains a ':' and is less than 12 characters (to catch stray emotes)
        # if message.content.find(':') != -1 and len(message.content) < 12:
        #     return
        index1 = transl_msg.find('<')  # type int
        index2 = transl_msg.find('>')
        if index1 > -1 and index2 > -1:  # if we found two indexes
            # contains the str for the emote
            emote = transl_msg[index1:index2+1]
            # remove all the " " inside the emote (hopefully this makes it output properly)
            emote = emote.replace(" ", "")
            main_txt = transl_msg[0:index1]
            await message.channel.send(main_txt + emote)
        else:
            await message.channel.send(transl_msg)
    if message.content == "a":
        await message.channel.send("サメです！")

# i just want the emotes to translate through well

client.run(TOKEN)
translate.run(TRANSLATE)

# testing...
# result = re.search('(.*)', message.content)
# elif client.hash(message.content) != 0: # if the message does not contain an emote
#     await message.channel.send