# bot.py
from operator import indexOf
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
    if translate_client.detect_language(message.content)["language"] != "en" and translate_client.detect_language(message.content)["confidence"] > 0.95:
        transl_msg = translate_client.translate(message.content, "en", "text")[
            "translatedText"]  # transl_msg = translated form of message
        # if the message contains a ':' and is less than 12 characters (to catch stray emotes)
        # if message.content.find(':') != -1 and len(message.content) < 12:
        #     return

        # so that the bot does not re-output links
        if message.content.startswith("https://"):
            return

        # making the emotes format themselves properly!
        if "<:" in message.content and ":>" in message.content:
            indices_open = [i.start() for i in re.finditer('<', transl_msg)]
            indices_closed = [i.start() for i in re.finditer('>', transl_msg)]
            # index1 = transl_msg.find('<')  # location of the first '<'
            # index2 = transl_msg.find('>')

            # if there's an emote there should be equal number of < and >
            for i in indices_open:
                emote = transl_msg[indices_open:indices_closed] # contains the str for the emote
            # remove all the " " inside the emote (hopefully this makes it output properly)
                emote = emote.replace(" ", "")
            # all the text that does not contain the emotes
                main_txt = transl_msg[0:indices_open]
            await message.channel.send(main_txt + emote)
        else:
            await message.channel.send(transl_msg)

    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")

# i just want the emotes to translate through well

client.run(TOKEN)
translate.run(TRANSLATE)

# testing...
# result = re.search('(.*)', message.content)
# elif client.hash(message.content) != 0: # if the message does not contain an emote
#     await message.channel.send
