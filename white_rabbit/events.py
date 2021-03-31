import datetime
from datetime import date, timedelta
from itertools import groupby
from typing import List, TypedDict, Dict, Iterable

import requests

from icalendar import Calendar

from white_rabbit.models import Employee
from white_rabbit.utils import start_of_day


class Event(TypedDict):
    name: str
    duration: float
    day: datetime.date


EventsPerEmployee = Dict[Employee, List[Event]]


def read_events(calendar_data: str) -> List[Event]:
    """Read events from an ical calendar and returns them as a list."""
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
    """Read events from an ical calendar available at given URL."""
    r = requests.get(url)
    data = r.content.decode()
    return read_events(data)


def get_all_events_per_employee(
    employees: Iterable[Employee] = None,
) -> EventsPerEmployee:
    if employees is None:
        employees = Employee.objects.all()
    return {
        employee: get_events_by_url(employee.calendar_ical_url)
        for employee in employees
    }


def events_per_day(events: List[Event], start_date: date, end_date: date):
    """
    Returns a dict day -> events for day for each day from start date to end
    date (included).
    Days without events are included.
    """
    delta = end_date - start_date
    events = [event for event in events if start_date <= event["day"] <= end_date]
    events_per_day = group_events_by_day(events)

    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        if day not in events_per_day:
            events_per_day[day] = []

    return events_per_day


def group_events_by_day(events: List[Event]) -> Dict[datetime.date, List[Event]]:
    """Returns a dict day -> events for day."""
    return {k: list(g) for k, g in groupby(events, lambda x: x["day"])}
