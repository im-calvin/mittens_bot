from googleapiclient.discovery import build
import google_auth_oauthlib
import googleapiclient.discovery
import googleapiclient.errors
from dotenv import load_dotenv
import os
import dateparser as dp
from datetime import date, datetime, time
from pytz import timezone
from src.helper import *

load_dotenv()
TRANSLATE_TOKEN = os.getenv('TRANSLATE_TOKEN')
YTClient = build("youtube", "v3", developerKey=TRANSLATE_TOKEN)

tsukushi_id = 'UC5XQhzMH08PgWa4Zp02Gcsw'
watame_id = 'UCqm3BQLlJfvkTsX_hvm0UmA'

# gets scheduled stream from chID where chID is ytChID and appends into holo_schedule


def getScheduledStreams(chID, holo_schedule):
    request = YTClient.search().list(
        part="id,snippet",
        channelId=chID,
        eventType="upcoming",
        type="video",
        order="date",
        maxResults=5
    )
    response = request.execute()

    for item in response['items']:
        id = item['id']['videoId']
        yt_url = f'https://www.youtube.com/watch?v={id}'
        # if there is a thing in the list > 0
        if (len([yt_url for entry in holo_schedule if entry['url'] == yt_url]) > 0):
            continue
        # iso_time = item['snippet']['publishedAt']  # time in RFC3339 format ; this actually gives published time
        title = item['snippet']['title']
        ch_name = item['snippet']['channelTitle']
        # start collab title updater:
        request_new = YTClient.videos().list(
            part="snippet,id,liveStreamingDetails",
            id=id)
        response_new = request_new.execute()
        iso_time = response_new['items'][0]['liveStreamingDetails']['scheduledStartTime']
        # description = response['items'][0]['snippet']['description']
        ##
        # convert ISO 8601 since RFC 3339 is subtype of ISO 8601 into Unix
        settings = {'TIMEZONE': 'UTC',
                    'TO_TIMEZONE': 'Asia/Tokyo'}
        parse = dp.parse(iso_time, settings=settings)
        parse = parse.astimezone(tz=timezone('Asia/Tokyo'))
        today_date = datetime.now(tz=timezone('Asia/Tokyo')).date()
        schedule_date = date(parse.year, parse.month, parse.day)
        schedule_time = time(parse.hour, parse.minute, parse.second,
                             parse.microsecond, tzinfo=timezone('Asia/Tokyo'))
        holo_date = ""
        if (today_date == schedule_date):
            holo_date = "today"
        else:
            holo_date = "tomorrow"
        schedule_time_string = schedule_time.strftime('%H:%M')
        unix_time = time_convert(schedule_time_string.split(':'), holo_date)
        holo_schedule.append({
            "time": schedule_time_string,
            "member": [ch_name],
            "url": yt_url,
            "title": title,
            "date": "today",
            "mentioned": False,
            "live_pinged": False,
            "true_date": unix_time
        })


# getScheduledStreams(watame_id, [])
