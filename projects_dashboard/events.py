import datetime
from typing import List, TypedDict

import requests

from icalendar import Calendar

from projects_dashboard.utils import start_of_day


class Event(TypedDict):
    name: str
    duration: float
    day: datetime.date


def read_events(calendar_data: str) -> List[Event]:
    cal = Calendar().from_ical(calendar_data)
    events: List[Event] = []
    for event in cal.walk():
        if event.name != "VEVENT":
            continue
        start = event["DTSTART"].dt
        end = event["DTEND"].dt

        # events can be on multiple days
        while start < end:
            start_day = start
            if isinstance(start_day, datetime.datetime):
                start_day = start_day.date()
            events.append(
                {
                    "name": event["SUMMARY"].title(),
                    "day": start_day,
                    "duration": min((end - start).total_seconds() / 3600, 24),
                }
            )
            start = start_of_day(start + datetime.timedelta(days=1))

    return sorted(events, key=lambda event: event["day"])


def get_events_by_url(url: str) -> List[Event]:
    r = requests.get(url)
    data = r.content.decode()
    return read_events(data)
