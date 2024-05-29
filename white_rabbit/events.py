import datetime
from datetime import date, timedelta
from typing import List, Dict, Iterable, Any

import requests
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from icalendar import Calendar

from white_rabbit.available_time import available_time_of_employee
from white_rabbit.constants import DEFAULT_NB_WORKING_HOURS
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.settings import DEFAULT_CACHE_DURATION
from white_rabbit.typing import EventsPerEmployee, Event, ProjectDistribution
from white_rabbit.utils import (
    start_of_day,
    calculate_period_start,
    calculate_period_key,
    group_events_by_day,
    generate_time_periods,
    count_number_days_spent_per_project_category,
    group_events_per_category,
    filter_events_per_time_period,
    day_distribution,
)


def read_events(
    calendar_data: str, employee: Employee, project_finder=None
) -> Iterable[Event]:
    """Read events from an ical calendar and returns them as a list."""
    cal = Calendar().from_ical(calendar_data)

    if project_finder is None:
        project_finder = ProjectFinder()

    events = [
        event
        for event in cal.walk()
        if event.name == "VEVENT"
        and event.get("SUMMARY")
        and not event["SUMMARY"].startswith("!")
    ]

    events_data: List[Event] = []
    for event in events:
        start_datetime = event["DTSTART"].dt

        try:
            end = event["DTEND"].dt
        except KeyError:
            end = start_datetime + datetime.timedelta(hours=1)

        start_date = (
            start_datetime.date()
            if isinstance(start_datetime, datetime.datetime)
            else start_datetime
        )
        if start_date < employee.start_time_tracking_from:
            continue

        calendar_name = event["SUMMARY"].split(" - ")[0]

        # events can be on multiple days
        next_day_start = start_of_day(start_datetime + datetime.timedelta(days=1))

        while start_datetime < end:
            event_data = get_event_data(
                start_datetime, end, calendar_name, project_finder, employee
            )
            events_data.append(event_data)
            events_data = sorted(
                events_data,
                key=lambda ev: ev["start_datetime"].date()
                if isinstance(ev["start_datetime"], datetime.datetime)
                else ev["start_datetime"],
            )
            start_datetime = next_day_start
            next_day_start = start_of_day(start_datetime + datetime.timedelta(days=1))

    return events_data


def get_event_data(start, end, calendar_name, project_finder, employee) -> Event:
    start_datetime = start

    project_name = calendar_name.split(" [")[0]
    subproject_name = None
    if len(calendar_name.split(" [")) > 1:
        subproject_name = (
            calendar_name[calendar_name.find("[") + 1 : calendar_name.find("]")]
            .strip()
            .lower()
        )

    project = project_finder.get_project(project_name, employee.company, start_datetime)

    return {
        "project_id": project.pk,
        "category": project.category,
        "name": project_name,
        "subproject_name": subproject_name,
        "start_datetime": start_datetime,
        "end_datetime": end,
        "duration": min((end - start).total_seconds() / 3600, DEFAULT_NB_WORKING_HOURS),
    }


def get_events_by_url(
    url: str, employee: Employee, project_finder=None
) -> Iterable[Event]:
    """Read events from an ical calendar available at given URL."""

    r = requests.get(url)
    data = r.content.decode()
    return read_events(data, employee, project_finder=project_finder)


def process_employee_events(
    employee: Employee, project_finder=None, request=None
) -> Iterable[Event]:
    if employee.start_time_tracking_from > datetime.date.today():
        return []

    try:
        return get_events_by_url(employee.calendar_ical_url, employee, project_finder)
    except ValueError:
        message = (
            f"Impossible de récupérer le calendrier de {employee}. Il doit être "
            "mal configuré. Dans sa configuration, bien mettre l'\"adresse "  # codespell:ignore
            'secrète au format iCal" de son calendrier'
        )
        if request:
            messages.error(request, message)
        else:
            print(message)
        return []


def create_events(
    employees: List[Employee], project_finder=None, request=None
) -> EventsPerEmployee:
    events: EventsPerEmployee = {}
    for employee in employees:
        events[employee] = process_employee_events(employee, project_finder, request)
    return events


def get_events_from_employees_from_cache(
    employees: List[Employee], project_finder=None, request=None
) -> EventsPerEmployee:
    events: EventsPerEmployee = {}
    for employee in employees:
        if employee_data := cache.get(str(employee.id), None):
            print("got from cache", employee.pk)
            events[employee] = employee_data
        else:
            print("fetching from ical", employee.pk)
            events[employee] = process_employee_events(
                employee, project_finder, request
            )
            cache.set(str(employee.id), events[employee], DEFAULT_CACHE_DURATION)
    return events


def employees_for_user(user: User) -> List[Employee]:
    company = user.employee.company
    if company.is_admin(user):
        return list(
            company.employees.filter(
                start_time_tracking_from__isnull=False,
                start_time_tracking_from__lte=datetime.date.today(),
                disabled=False,
            )
        )

    if user.employee.start_time_tracking_from:
        return [user.employee]

    return []


def events_per_day(
    events: Iterable[Event], start_datetime: date, end_datetime: date
) -> Dict[datetime.date, Iterable[Event]]:
    """
    Returns a dict day -> events for day for each day from start date to end
    date (included).
    Days without events are included.
    """
    delta = end_datetime - start_datetime
    events = [
        event
        for event in events
        if start_datetime <= event["start_datetime"] <= end_datetime
    ]
    to_return = group_events_by_day(events)

    # also include days without events
    for i in range(delta.days + 1):
        day = start_datetime + timedelta(days=i)
        if day not in to_return:
            to_return[day] = []

    return to_return


class EmployeeEvents:
    def __init__(self, employee: Employee, events, n_periods=12):
        self.employee = employee
        self.events = events
        self.n_periods = n_periods

    @property
    def employee_name(self):
        return self.employee.name

    def group_events_per_day(self):
        return group_events_by_day(self.events)

    def filter_events_per_month(self, date: datetime):
        events = [
            event
            for event in self.events
            if event["start_datetime"].month == date.month
        ]
        return {date: events}

    @property
    def data(self):
        return {
            "employee": self.employee_name,
            "events": self.events,
            "projects": self.projects,
        }

    def group_events_per_project_category(self, month=None, week=None):
        projects = {}

        events_per_category = group_events_per_category(self.events)

        for _event_category, events in events_per_category.items():
            if month or week:
                time_period = week if week else month
                filtered_events_per_category = filter_events_per_time_period(
                    events, time_period
                )

            number_days_spent_per_project_category = (
                count_number_days_spent_per_project_category(
                    filtered_events_per_category,
                    self.employee.min_working_hours_for_full_day,
                )
            )
            projects.update(number_days_spent_per_project_category)

        return projects

    def group_by_time_period(
        self,
        time_period: str = "month",
        n_periods: int = None,
        timeshift_direction="past",
    ):
        events: Any = {}

        if n_periods is None:
            n_periods = self.n_periods

        periods = generate_time_periods(n_periods, time_period, timeshift_direction)
        for period in periods:
            events[period["key"]] = {
                "availability": available_time_of_employee(
                    self.employee, self.events, period["start"], period["end"]
                ),
                "events": filter_events_per_time_period(
                    self.events, period["start"], time_period
                ),
            }
        return events

    def total_per_time_period_and_project_category(
        self,
        time_period: str = "month",
        n_periods: int = None,
        timeshift_direction="past",
    ):
        if n_periods is None:
            n_periods = self.n_periods
        events: Any = {}
        for period_index in range(n_periods):
            period_start = calculate_period_start(
                period_index, time_period, timeshift_direction
            )
            period_key = calculate_period_key(period_start, time_period)
            events[period_key] = self.group_events_per_project_category(
                **{time_period: period_start}
            )

        return events

    def projects_for_time_period(
        self,
        period: str,
        time_period: str = "month",
    ):

        events: Any = {}

        filtered_events = filter_events_per_time_period(
            self.events, period["start"], time_period
        )
        for event_date, events_for_day in group_events_by_day(filtered_events).items():
            distribution: Dict[int, ProjectDistribution] = day_distribution(
                events_for_day, employee=self.employee
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

        # events[period["key"]] = count_number_days_spent_per_project(filtered_events)
        return events


def process_employees_events(  # noqa: C901
    events_per_employee: EventsPerEmployee,
    n_periods: int = 12,
):
    employees = {}
    for employee_instance, employee_events in events_per_employee.items():
        employees[employee_instance.name] = EmployeeEvents(
            employee_instance, employee_events, n_periods
        )
    return employees
