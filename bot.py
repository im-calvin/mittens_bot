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
async def on_ready():
    print("もしもし")


@client.event
async def on_message(message):
    if message.author == client.user:  # base case
        return
    # if jap is detected & the confidence is high
    if translate_client.detect_language(message.content)["language"] != "en" and translate_client.detect_language(message.content)["confidence"] > 0.95:
        transl_msg = translate_client.translate(message.content, "en", "text")[
            "translatedText"]  # transl_msg = translated form of message

        # so that the bot does not re-output links
        if message.content.startswith("https://"):
            return

        # making the emotes format themselves properly!
        if "<:" in message.content and ">" in transl_msg:
            # "indices_open" is the list that contains the index's for the '<' char
            indices_open = [i.start() for i in re.finditer('<', transl_msg)]
            indices_closed = [i.start() for i in re.finditer('>', transl_msg)]

            # if there's an emote there should be equal number of < and >
            for i in range(len(indices_open)):
                # splicing each emote from transl_msg into a list of str
                emote = [transl_msg[indices_open[i]:indices_closed[i]]]
            # remove all the " " inside the emote
                emote[i] = emote[i].replace(" ", "")
                # text after first emote and before second emote
                j = 0
                while j < len(indices_open)-1:
                    main_txt = [
                        transl_msg[indices_closed[j]:indices_open[j+1]]]
                    j += 1
                # all the text between the first and last emote
                body_txt = emote[i] + main_txt[i]
            # all the text that does not contain the emotes
            # text before first emote
            main_txt_start = transl_msg[0:indices_open[0]]
            main_txt_end = transl_msg[indices_closed[len(indices_closed)]:len(
                transl_msg)]  # text after last emote
            await message.channel.send(main_txt_start + body_txt + main_txt_end)
        else:
            await message.channel.send(transl_msg)

    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")


client.run(TOKEN)
translate.run(TRANSLATE)
