import datetime
from datetime import date, timedelta
from itertools import groupby
from typing import List, TypedDict, Dict, Iterable

import requests
from django.contrib.auth.models import User
from django.db.models import Q

from icalendar import Calendar

from white_rabbit.constants import ALIASES
from white_rabbit.models import Employee, Alias, Project
from white_rabbit.utils import start_of_day


class Event(TypedDict):
    name: str
    duration: float
    day: datetime.date


EventsPerEmployee = Dict[Employee, Iterable[Event]]


def event_name_from_calendar_summary(event_summary):

    # TODO: remplire les nom de projet ou d'Aliases : et mettre dans admin la possibiltié de les gérer : ici si pas Alias ou pas projet alors crée un nouveau projet

    name = event_summary.split(" - ")[0]
    name = name.title()
    # for alias in ALIASES:
    #     if name.lower() in ALIASES[alias]:
    #         return alias
    # Alias.objects.filter(Q(project__name=name.lower()) | Q(name))
    project = Project.objects.filter(Q(name=name.lower()) | Q(aliases__name=name.lower()))
    if project.exists():
        project = project.get()
    else:
        project = Project(name=name.lower())
        project.save()
    return project.name.capitalize()


def read_events(calendar_data: str) -> Iterable[Event]:
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
                    "name": event_name_from_calendar_summary(event["SUMMARY"]),
                    "day": start_day,
                    "duration": min((end - start).total_seconds() / 3600, 24),
                }
            )
            start = start_of_day(start + datetime.timedelta(days=1))

    return sorted(events, key=lambda event: event["day"])


def get_events_by_url(url: str) -> Iterable[Event]:
    """Read events from an ical calendar available at given URL."""
    r = requests.get(url)
    data = r.content.decode()
    return read_events(data)


def get_events_for_employee(employee: Employee):
    return get_events_by_url(employee.calendar_ical_url)


def get_events_for_employees(employees: Iterable[Employee]) -> EventsPerEmployee:
    if employees is None:
        employees = Employee.objects.all()
    return {
        employee: get_events_by_url(employee.calendar_ical_url)
        for employee in employees
    }


def employees_for_user(user: User) -> Iterable[Employee]:
    company = user.employee.company
    if company.is_admin(user):
        return company.employee_set.filter(start_time_tracking_from__isnull=False)

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
