# bot.py
import os
from socket import MsgFlag

import discord
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from discord.ext import commands
import re
import asyncio
# from jisho_api.word import Word
# from jisho_api.kanji import Kanji

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
TRANSLATE = os.getenv('TRANSLATE_TOKEN')

client = discord.Client()
translate_client = translate.Client.from_service_account_json(
    'googleapi.json')


def sanitizer(msg):
    while True:
        # since slicing is exclusive of index1, inclusive of index2
        index1 = msg.find('<')
        index2 = msg.find('>') + 1
        msg = msg.replace(
            msg[index1:index2], "")
        if msg.find('<') == -1:
            return


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
    # for gura-chan
    if message.content == "a":
        await message.channel.send("サメです！")
    lang = translate_client.detect_language(message.content)["language"]

    if lang == "ja" or lang == "zh-CN" or lang == "zh-TW" or lang == "fr" or lang == "ko":
        # zh-TW = traditional, zh-CN = simplified
        if translate_client.detect_language(message.content)["confidence"] > 0.95:
            transl_msg = translate_client.translate(message.content, "en", "text")[
                "translatedText"]  # transl_msg = translated form of message

            if "@" in transl_msg:
                transl_msg = transl_msg.replace("@ ", "@")

        # making the emotes format themselves properly!
            if (("<:" in transl_msg and ">" in transl_msg) or ("<a:" in transl_msg and ">" in transl_msg)):
                sanitizer(transl_msg)
            bot_msg = await message.channel.send(transl_msg)
            global bot_id
            bot_id = bot_msg.id
            bot_msg


@client.event
async def on_message_edit(before, after):
    channel = after.channel # channel object
    message = await channel.fetch_message(bot_id) # message object (from user)

    lang = translate_client.detect_language(after.content)["language"]

    if lang == "ja" or lang == "zh-CN" or lang == "zh-TW" or lang == "fr" or lang == "ko":
        # zh-TW = traditional, zh-CN = simplified
        if translate_client.detect_language(after.content)["confidence"] > 0.95:
            transl_msg = translate_client.translate(after.content, "en", "text")[
                "translatedText"]  # transl_msg = translated form of message

            if "@" in transl_msg:
                transl_msg = transl_msg.replace("@ ", "@")

        # making the emotes format themselves properly!
            if (("<:" in transl_msg and ">" in transl_msg) or ("<a:" in transl_msg and ">" in transl_msg)):
                sanitizer(transl_msg)
            await message.edit(content=transl_msg)

client.run(TOKEN)
