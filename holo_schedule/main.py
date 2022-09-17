# Fetch the schedule of hololive live stream
# creds: https://github.com/TBNV999/holo-schedule-CLI

import sys
import unicodedata
import argparse
import json

from holo_schedule.src.fetch_html import *
from holo_schedule.src.scraping import *
from holo_schedule.src.util import *

LABELS = ("Yesterday", "Today", "Tomorrow", "The day after tomorrow")


def main(args, holo_list):

    if args.date:
        show_date()
        sys.exit(0)

    timezone = check_timezone()

    # Fetch html file from https://schedule.hololive.tv/simple
    try:  # if no streams tmr
        source_html = fetch_source_html(args.tomorrow)
    except SystemExit:
        print('no streams scheduled for tomorrow')
        return
    time_list, members_list, url_list = scraping(source_html, args.all)

    if args.future and not args.tomorrow:
        hour_list = list(map(lambda x: int(x.split(':')[0]), time_list))
        filter_map = filter_future(hour_list)
    else:
        filter_map = [True] * len(time_list)

    if timezone != 'Asia/Tokyo':
        time_list = timezone_convert(time_list, timezone)
        date_delta = get_date_delta(timezone)
    else:
        date_delta = 0

    if args.tomorrow:
        date_delta += 1

    # All three lists have the same length
    lists_length = len(time_list)

    members_list = list(map(replace_name, members_list))
    hour_list = list(map(lambda x: int(x.split(':')[0]), time_list))

    # Check if date is shifted
    if hour_list != sorted(hour_list):
        shift_index = check_shift(hour_list)
    else:
        shift_index = None

    title_list = []

    if args.title:
        title_list = fetch_title(url_list)

    # Convert member's name into English
    if args.eng:
        members_list = convert_into_en_list(members_list)

    for i, (time, member, url) in enumerate(zip(time_list, members_list, url_list)):
        if not filter_map[i]:
            continue

        # Contain Japanese
        if unicodedata.east_asian_width(members_list[i][0]) == 'W':
            m_space = ' ' * ((-2 * len(members_list[i]) + 18))

        else:
            m_space = ' ' * ((-1 * len(members_list[i])) + 18)

        # With titles of streams
        try:
            if args.title and not args.tomorrow:
                # always going to have args.title in json
                # updating json file:
                holo_list.append({
                    "time": time,
                    "member": [member],
                    "url": url,
                    "title": title_list[i],
                    "date": "today",
                    "mentioned": False,
                    "live_pinged": False
                }
                )
                    
            else:  # if args.tomorrow

                holo_list.append({
                    "time": time,
                    "member": [member],
                    "url": url,
                    "title": title_list[i],
                    "date": "tomorrow",
                    "mentioned": False,
                    "live_pinged": False
                }
                )
        # Some emoji cause this error
        except UnicodeEncodeError:
            title_list[i] = remove_emoji(title_list[i])
            continue

    with open('holo_schedule.json', "w") as f:
        # replace the old json file every 15m -- write only!
        # exports json file
        json.dump(holo_list, f, indent=4)

    return holo_list
