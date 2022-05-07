# bot.py
import os

import discord
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
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
    if message.author == client.user:
        return
    if translate_client.detect_language(message.content)["language"] == "ja" and translate_client.detect_language(message.content)["confidence"] > 0.95:
        if message.content.find(':') != -1 and len(message.content) < 12:
            return
        else:
            await message.channel.send(translate_client.translate(
                message.content, "en", "text")["translatedText"])
    elif message.content == "a":
        await message.channel.send("サメです！")
client.run(TOKEN)
translate.run(TRANSLATE)
