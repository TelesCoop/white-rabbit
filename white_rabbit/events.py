import datetime
from bisect import insort
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
from itertools import groupby
from typing import List, TypedDict, Dict, Iterable, Union
from django.core.cache import cache

import requests
from django.contrib.auth.models import User
from icalendar import Calendar
from django.contrib import messages

from white_rabbit.constants import DEFAULT_ROUND_DURATION_PRECISION
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectNameFinder
from white_rabbit.settings import DEFAULT_CACHE_DURATION
from white_rabbit.typing import EventsPerEmployee, Event, MonthDetailPerEmployeePerMonth, ProjectDistribution, \
    ProjectTime
from white_rabbit.utils import start_of_day



def read_events(
        calendar_data: str, employee: Employee, project_name_finder=None
) -> Iterable[Event]:
    """Read events from an ical calendar and returns them as a list."""
    cal = Calendar().from_ical(calendar_data)

    if project_name_finder is None:
        project_name_finder = ProjectNameFinder()

    events = [
        event for event in cal.walk()
        if event.name == "VEVENT" and event.get("SUMMARY") and not event["SUMMARY"].startswith("!")
    ]

    events_data: List[Event] = []
    for event in events:
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

        calendar_name = event["SUMMARY"].split(" - ")[0]

        # events can be on multiple days
        next_day_start = start_of_day(start + datetime.timedelta(days=1))
        while start < end:
            event_data = get_event_data(start, end, calendar_name, project_name_finder, employee)
            insort(events_data, event_data, key=lambda ev: ev["day"])
            start = next_day_start
            next_day_start = start_of_day(start + datetime.timedelta(days=1))

    return events_data


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

    events = cache.get('events', None)
    if events is None:
        events: EventsPerEmployee = {}
        for employee in employees:
            if employee.start_time_tracking_from > datetime.date.today():
                events[employee] = []
                continue
            try:
                events[employee] = get_events_by_url(
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
                events[employee] = []
        cache.set('events', events, DEFAULT_CACHE_DURATION)
    return events


def employees_for_user(user: User) -> List[Employee]:
    company = user.employee.company
    if company.is_admin(user):
        return list(
            company.employees.filter(
                start_time_tracking_from__isnull=False,
                start_time_tracking_from__lte=datetime.date.today(),
                disabled=False
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


def day_distribution(
        events: Iterable[Event], employee: Employee
) -> Dict[int, ProjectDistribution]:
    """
    Given all events for a day for an employee, count the number of days
    (<= 1) spent on each project.
    """
    total_time = sum(event["duration"] for event in events)
    is_full_day = total_time >= employee.min_working_hours_for_full_day
    if is_full_day:
        divider = total_time
    else:
        divider = float(employee.default_day_working_hours)

    distribution: Dict[int, ProjectDistribution] = defaultdict(
        lambda: {"duration": 0.0, "subproject_name": ""}
    )

    for event in events:
        distribution[event["project_id"]]["subproject_name"] = event["subproject_name"]
        distribution[event["project_id"]]["duration"] += event["duration"] / divider

    return dict(distribution)

def month_detail_per_employee_per_month(  # noqa: C901
        events_per_employee: EventsPerEmployee,
        month: datetime.date = None,
        week: datetime.date = None,
) -> MonthDetailPerEmployeePerMonth:
    """
    Counts the number of days spent per project for selected month or week.

    If week and month are None, counts the historical total.
    """
    to_return_1: Dict[str, Dict[str, Dict[int, ProjectTime]]] = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: {
                    "duration": 0.0,
                    "events": [],
                    "subprojects": defaultdict(lambda: {"duration": 0.0}),
                }
            )
        )
    )
    # make sure specific keys exist and are at the start
    to_return_1["Total"]["Total"]  # noqa
    to_return_1["Total"]["Total effectué"]  # noqa
    to_return_1["Total"]["Total à venir"]  # noqa

    for employee, employee_events in events_per_employee.items():
        for event_date, events_for_day in group_events_by_day(employee_events).items():
            if month and (event_date.month, event_date.year) != (
                    month.month,
                    month.year,
            ):
                continue
            if week and (event_date.isocalendar()[:2] != week.isocalendar()[:2]):
                continue

            # format : YY-MM
            month_label = f"{event_date.strftime('%b %y')}"

            distribution: Dict[int, ProjectDistribution] = day_distribution(
                events_for_day, employee=employee
            )

            date_keys_to_update = ["Total", month_label]
            if event_date <= datetime.date.today():
                date_keys_to_update.append("Total effectué")
            else:
                date_keys_to_update.append("Total à venir")

            for project_id, details in distribution.items():
                # add both to total and relevant employee
                duration = details["duration"]  # type: ignore
                subproject_name = details["subproject_name"]  # type: ignore
                for employee_key in ["Total", employee.name]:
                    # add values both to total and relevant month
                    for date_key in date_keys_to_update:
                        to_return_1[employee_key][date_key][project_id][
                            "duration"
                        ] += duration
                        if subproject_name:
                            to_return_1[employee_key][date_key][project_id][
                                "subprojects"
                            ][subproject_name]["duration"] += duration
                        to_return_1[employee_key][date_key][project_id][
                            "events"
                        ].append(
                            {
                                "employee": employee.name,
                                "date": event_date,
                                "duration": duration,
                            }
                        )

    to_return: MonthDetailPerEmployeePerMonth = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: {
                    "order": [],
                    "values": {
                        "duration": 0.0,
                        "events": [],
                        "subprojects": defaultdict(lambda: {"duration": 0.0}),
                    },
                }
            )
        )
    )

    # sort by total duration for each month and total and keep order
    for employee_key, employee_values in to_return_1.items():
        for display_month, time_per_project in employee_values.items():
            project_ids_ordered = sorted(
                time_per_project.keys(),
                key=lambda project_id: time_per_project[project_id]["duration"],
                reverse=True,
            )
            to_return[employee_key][display_month] = {
                "order": project_ids_ordered,
                "values": time_per_project,
            }

    return to_return