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
    if message.content.startswith("https://"):
        return
    if message.content.startswith("<:"):
        return
    lang = translate_client.detect_language(message.content)["language"]

    # if jap is detected & the confidence is high
    if lang == "ja" or lang == "zh" or lang == "fr" or lang == "ko":
        if translate_client.detect_language(message.content)["confidence"] > 0.9:
            transl_msg = translate_client.translate(message.content, "en", "text")[
                "translatedText"]  # transl_msg = translated form of message

            if "@" in transl_msg:
                transl_msg = transl_msg.replace("@ ", "@")

        # making the emotes format themselves properly!
            if (("<:" in transl_msg and ">" in transl_msg) or ("<a:" in transl_msg and ">" in transl_msg)):
                # sanitizer function
                while True:
                    # since slicing is exclusive of index1, inclusive of index2
                    index1 = transl_msg.find('<')
                    index2 = transl_msg.find('>') + 1
                    transl_msg = transl_msg.replace(
                        transl_msg[index1:index2], "")
                    if transl_msg.find('<') == -1:
                        break
            await message.channel.send(transl_msg)

    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")


client.run(TOKEN)
