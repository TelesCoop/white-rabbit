import datetime
from bisect import insort
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
from itertools import groupby
from typing import List, TypedDict, Dict, Iterable, Union, DefaultDict, Any, Counter
from django.core.cache import cache

import requests
from django.contrib.auth.models import User
from icalendar import Calendar
from django.contrib import messages
from dateutil.relativedelta import relativedelta

from white_rabbit.available_time import available_time_of_employee
from white_rabbit.constants import DEFAULT_ROUND_DURATION_PRECISION
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectNameFinder
from white_rabbit.settings import DEFAULT_CACHE_DURATION
from white_rabbit.typing import EventsPerEmployee, Event, MonthDetailPerEmployeePerMonth, ProjectDistribution, \
    ProjectTime
from white_rabbit.utils import start_of_day, count_number_days_spent_per_project, get_period_start, \
    calculate_period_key, group_events_by_day, generate_time_periods


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
            calendar_name[calendar_name.find("[") + 1: calendar_name.find("]")]
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


def process_employee_events(employee: Employee, project_name_finder=None, request=None) -> Iterable[Event]:
    if employee.start_time_tracking_from > datetime.date.today():
        return []

    try:
        return get_events_by_url(employee.calendar_ical_url, employee, project_name_finder)
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
        return []


def create_events(employees: List[Employee], project_name_finder=None, request=None) -> EventsPerEmployee:
    events: EventsPerEmployee = {}
    for employee in employees:
        events[employee] = process_employee_events(employee, project_name_finder, request)
    return events


def get_events_from_employees_from_cache(
        employees: List[Employee], project_name_finder=None, request=None
) -> EventsPerEmployee:
    events = cache.get('events', None)
    if events is None:
        events = create_events(employees, project_name_finder, request)
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


class ProjectEventsTracker:
    def __init__(self, total_duration=0, days_spent=0, events=None, subprojects=None):
        if events is None:
            events = []
        if subprojects is None:
            subprojects = {}
        self.total_duration = total_duration
        self.days_spent = days_spent
        self.events = events
        self.subprojects = subprojects

    def add_total_duration(self, duration):
        self.total_duration += duration

    def add_total_days_spent(self, days_spent):
        self.days_spent += days_spent

    def add(self, event):
        self.add_total_duration(event['duration'])
        self.add_total_days_spent(event['days_spent'])
        self.events.append(event)

    def add_subproject_duration(self, subproject_name, duration):
        if subproject_name not in self.subprojects:
            self.subprojects[subproject_name] = 0.0
        self.subprojects[subproject_name] += duration


class EmployeeEvents:
    def __init__(self, employee: Employee, events, upcoming_periods=12):
        self.employee = employee
        self.events = events
        self.projects = {}
        self.n_upcoming_periods = upcoming_periods

    @property
    def employee_name(self):
        return self.employee.name

    def add_project_by_id(self, project_id):
        if project_id not in self.projects:
            self.projects[project_id] = ProjectEventsTracker()

    def get_or_create_project_by_id(self, project_id):
        if self.projects.get(project_id, None) is None:
            self.add_project_by_id(project_id)
        return self.projects.get(project_id)

    @property
    def events_per_day(self):
        return group_events_by_day(self.events)

    def filter_events_per_month(self, date: datetime):
        events = [event for event in self.events if event["day"].month == date.month]
        return {date: events}

    @property
    def data(self):
        return {
            "employee": self.employee_name,
            "events": self.events,
            "projects": self.projects
        }

    def process_events_per_projects(self, month=None, week=None):
        projects = {}

        for event_date, events_for_day in self.events_per_day.items():
            if month and (event_date.month, event_date.year) != (
                    month.month,
                    month.year,
            ):
                continue
            if week and (event_date.isocalendar()[:2] != week.isocalendar()[:2]):
                continue

            number_days_spent_per_project = (count_number_days_spent_per_project(events_for_day, self.employee))

            for project_id, project_event_details in number_days_spent_per_project.items():
                duration = project_event_details["duration"]
                days_spent = project_event_details["days_spent"]
                subproject_name = project_event_details["subproject_name"]
                employee_name = self.employee.name

                if projects.get(project_id, None) is None:
                    if project_id not in projects:
                        projects[project_id] = ProjectEventsTracker()

                project = projects.get(project_id)

                if subproject_name:
                    project.add_subproject_duration(subproject_name, duration)

                project.add(
                    {
                        "project_id": project_id,
                        "employee": employee_name,
                        "date": event_date,
                        "duration": duration,
                        "days_spent": days_spent
                    }
                )
        return projects

    def _calculate_total_projects(self, employee, projects_total):
        return [proj[0] for proj in projects_total[employee].most_common()]

    def upcoming_events(self, time_period: str = "month", n_upcoming_periods: int = 12):
        events: Any = {}
        projects_total: DefaultDict = defaultdict(Counter)

        events[self.employee.name] = {}
        for period_index in range(n_upcoming_periods):

            period_start = get_period_start(period_index, time_period)

            period_end = (
                    period_start
                    + relativedelta(**{f"{time_period}s": 1})  # type: ignore
                    - relativedelta(days=1)
            )

            period_key = calculate_period_key(period_start, time_period)

            employee_data_events = self.process_events_per_projects(**{time_period: period_start})

            events[self.employee.name][period_key] = {
                "availability": available_time_of_employee(
                    self.employee,
                    self.events,
                    period_start,
                    period_end
                ),
                "projects": employee_data_events,
            }

            for project_id, event_data in employee_data_events.items():
                projects_total[self.employee.name][project_id] += event_data.total_duration

        events[self.employee.name]["projects_total"] = self._calculate_total_projects(self.employee, projects_total)

        return events

    def generate_time_periods(self, time_period: str = "month", n_upcoming_periods: int = None):
        if n_upcoming_periods is None:
            n_upcoming_periods = self.n_upcoming_periods
        return generate_time_periods(n_upcoming_periods, time_period)


def process_employees_events(  # noqa: C901
        events_per_employee: EventsPerEmployee,
        month: datetime.date = None,
        week: datetime.date = None,
        upcoming_periods: int = 12,
) -> MonthDetailPerEmployeePerMonth:
    employees = {}
    for employee_instance, employee_events in events_per_employee.items():
        employees[employee_instance.name] = EmployeeEvents(employee_instance, employee_events, upcoming_periods)
        employees[employee_instance.name].process_events_per_projects(month, week)
    return employees
