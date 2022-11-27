def translator(message, translate_client, sanitizer):
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


def deepl_translator(message, dlTrans, sanitizer):
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


async def kana(message, print_plaintext):
    channel = message.channel
    try:
        messageID = message.reference.message_id
    except AttributeError:  # if no reply
        await message.channel.send('You need to reply to a message')
        return

    message = await channel.fetch_message(messageID)

    kanaMsg = print_plaintext(message.content)

    await channel.send(kanaMsg)
