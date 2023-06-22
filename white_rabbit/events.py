import datetime
from datetime import date, timedelta
from itertools import groupby
from typing import List, TypedDict, Dict, Iterable, Union

import requests
from django.contrib.auth.models import User
from icalendar import Calendar
from django.contrib import messages

from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectNameFinder
from white_rabbit.utils import start_of_day


class Event(TypedDict):
    project_id: int
    name: str
    subproject_name: Union[str, None]
    duration: float
    day: datetime.date


EventsPerEmployee = Dict[Employee, Iterable[Event]]


def read_events(
    calendar_data: str, employee: Employee, project_name_finder=None
) -> Iterable[Event]:
    """Read events from an ical calendar and returns them as a list."""
    cal = Calendar().from_ical(calendar_data)
    events: List[Event] = []

    if project_name_finder is None:
        project_name_finder = ProjectNameFinder()

    for event in cal.walk():
        if event.name != "VEVENT" or not event.get("SUMMARY"):
            continue
        start = event["DTSTART"].dt
        try:
            end = event["DTEND"].dt
        except KeyError:
            end = start + datetime.timedelta(hours=1)

        # ignore events before start time tracking
        if isinstance(start, datetime.datetime):
            start_day = start.date()
        else:
            start_day = start
        if start_day < employee.start_time_tracking_from:
            continue

        # ignore events whose title starts with !
        if event["SUMMARY"].startswith("!"):
            continue

        calendar_name = event["SUMMARY"].split(" - ")[0]

        # events can be on multiple days
        while start < end:
            events.append(
                get_event_data(start, end, calendar_name, project_name_finder, employee)
            )
            start = start_of_day(start + datetime.timedelta(days=1))

    return sorted(events, key=lambda ev: ev["day"])


def get_event_data(start, end, calendar_name, project_name_finder, employee) -> Event:
    start_day = start
    if isinstance(start_day, datetime.datetime):
        start_day = start_day.date()

    project_name = calendar_name.split(" [")[0]
    subproject_name = None
    if len(calendar_name.split(" [")) > 1:
        subproject_name = (
            calendar_name[calendar_name.find("[") + 1 : calendar_name.find("]")]
            .strip()
            .lower()
        )
    return {
        "project_id": project_name_finder.get_project_id(
            project_name, employee.company, start_day
        ),
        "name": project_name,
        "subproject_name": subproject_name,
        "day": start_day,
        "duration": min((end - start).total_seconds() / 3600, 24),
    }


def get_events_by_url(
    url: str, employee: Employee, project_name_finder=None
) -> Iterable[Event]:
    """Read events from an ical calendar available at given URL."""
    r = requests.get(url)
    data = r.content.decode()
    return read_events(data, employee, project_name_finder=project_name_finder)


def get_events_for_employees(
    employees: List[Employee], project_name_finder=None, request=None
) -> EventsPerEmployee:
    to_return: EventsPerEmployee = {}
    for employee in employees:
        if employee.start_time_tracking_from > datetime.date.today():
            to_return[employee] = []
            continue
        try:
            to_return[employee] = get_events_by_url(
                employee.calendar_ical_url, employee, project_name_finder
            )
        except ValueError:
            message = (
                f"Impossible de récupérer le calendrier de {employee}. Il doit être "
                "mal configuré. Dans sa configuration, bien mettre l'\"Adresse "
                'secrète au format iCal" de son calendrier'
            )
            if request:
                messages.error(request, message)
            else:
                print(message)
            to_return[employee] = []

    return to_return


def employees_for_user(user: User) -> List[Employee]:
    company = user.employee.company
    if company.is_admin(user):
        return list(
            company.employees.filter(start_time_tracking_from__isnull=False).filter(
                start_time_tracking_from__lte=datetime.date.today()
            )
        )

    if user.employee.start_time_tracking_from:
        return [user.employee]

    return []


def events_per_day(
    events: Iterable[Event], start_date: date, end_date: date
) -> Dict[datetime.date, Iterable[Event]]:
    """
    Returns a dict day -> events for day for each day from start date to end
    date (included).
    Days without events are included.
    """
    delta = end_date - start_date
    events = [event for event in events if start_date <= event["day"] <= end_date]
    to_return = group_events_by_day(events)

    # also include days without events
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        if day not in to_return:
            to_return[day] = []

    return to_return


def group_events_by_day(
    events: Iterable[Event],
) -> Dict[datetime.date, Iterable[Event]]:
    """Returns a dict day -> events for day."""
    return {k: list(g) for k, g in groupby(events, lambda x: x["day"])}
