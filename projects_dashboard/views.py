import datetime
from collections import defaultdict, Counter
from datetime import date, timedelta
from itertools import groupby
from typing import List, Dict, Counter as TypingCounter

from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.views import View
from jours_feries_france import JoursFeries

from .constants import MIN_WORKING_HOURS_FOR_FULL_DAY, DEFAULT_DAY_WORKING_HOURS
from .events import get_events_by_url, Event
from .models import Employee


EventsPerEmployee = Dict[Employee, List[Event]]


def group_events_by_day(events: List[Event]) -> Dict[datetime.date, List[Event]]:
    """Returns a dict day -> events for day."""
    return {k: list(g) for k, g in groupby(events, lambda x: x["day"])}


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


def state_of_day(events: List[Event]) -> str:
    """Returns the state of a day as a string."""
    if not events:
        return "empty"
    total_duration = sum(event["duration"] for event in events)
    if not total_duration:
        return "empty"
    if total_duration < MIN_WORKING_HOURS_FOR_FULL_DAY:
        return "incomplete"
    return "complete"


def state_of_days(events: List[Event], start_date: date, end_date: date):
    per_day_events = events_per_day(events, start_date, end_date)
    return {day: state_of_day(events) for day, events in per_day_events.items()}


def state_of_days_per_employee(
    events_per_employee: EventsPerEmployee, start_date: date, end_date: date
) -> Dict[datetime.date, Dict[str, str]]:
    """
    Returns a dict date -> (employee -> state of day) for each
    combination, including days without events.
    """
    to_return: Dict[datetime.date, Dict[str, str]] = defaultdict(lambda: defaultdict())
    for employee, employee_events in events_per_employee.items():
        per_day_events = events_per_day(employee_events, start_date, end_date)
        for day, events in per_day_events.items():
            to_return[day][employee] = state_of_day(events)

    return dict(to_return)


def day_distribution(events: List[Event]) -> Dict[str, float]:
    """Given all events for a day for an employee, count the number of days (<= 1) spent on each project."""
    total_time = sum(event["duration"] for event in events)
    is_full_day = total_time >= MIN_WORKING_HOURS_FOR_FULL_DAY
    if is_full_day:
        divider = total_time
    else:
        divider = DEFAULT_DAY_WORKING_HOURS

    distribution: TypingCounter[str] = Counter()

    for event in events:
        distribution[event["name"]] += event["duration"] / divider  # type: ignore

    return dict(distribution)


def time_per_project(events_per_employee: EventsPerEmployee):
    """Counts the number of days spent per project."""
    to_return: TypingCounter[str] = Counter()
    for _, employee_events in events_per_employee.items():
        for _, events_for_day in group_events_by_day(employee_events).items():
            distribution = day_distribution(events_for_day)
            for name, duration in distribution.items():
                to_return[name] += duration  # type: ignore

    return dict(to_return)


def available_time_of_employee(
    employee, events: List[Event], start_date: date, end_date: date
):
    """Returns the number of working days that are available for an employee."""
    events_per_day = group_events_by_day(events)
    availability_duration = 0

    day = start_date - datetime.timedelta(days=1)
    while day < end_date:
        day += datetime.timedelta(days=1)
        # for weekend and bank holiday
        if day.weekday() >= 5 or JoursFeries.is_bank_holiday(day, zone="Métropole"):
            continue

        busy_duration = sum(event["duration"] for event in events_per_day.get(day, []))
        if busy_duration >= MIN_WORKING_HOURS_FOR_FULL_DAY:
            continue

        availability_duration += (
            max(employee.availability_per_day - busy_duration, 0)
            / employee.availability_per_day
        )

    return availability_duration


class HomeView(View):
    def get(self, request):
        employees = [
            Employee.objects.get(name="Maxime"),
            Employee.objects.get(name="Quentin"),
            Employee.objects.get(name="Antoine"),
        ]  # Employee.objects.all()
        events_per_employee: EventsPerEmployee = {
            employee: get_events_by_url(employee.calendar_ical_url)
            for employee in employees
        }

        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_next_week = today - datetime.timedelta(days=today.weekday())
        start_of_next_month = today.replace(day=1) + relativedelta(month=1)
        end_of_next_month = (
            start_of_next_month + relativedelta(month=1) - relativedelta(days=1)
        )
        end_of_week = start_of_week + datetime.timedelta(days=4)
        end_of_next_week = start_of_next_week + datetime.timedelta(days=4)

        context = {
            "events": events_per_employee,
            "employees": employees,
            "time_per_project": time_per_project(events_per_employee),
            "curent_week_state": state_of_days_per_employee(
                events_per_employee, start_of_week, end_of_week
            ),
            "state_of_days": {
                employee: state_of_days(events, date(2021, 3, 15), date(2021, 3, 22))
                for employee, events in events_per_employee.items()
            },
            "next_week_availability": {
                employee: available_time_of_employee(
                    employee, events, start_of_next_week, end_of_next_week
                )
                for employee, events in events_per_employee.items()
            },
            "next_month_availability": {
                employee: available_time_of_employee(
                    employee, events, start_of_next_month, end_of_next_month
                )
                for employee, events in events_per_employee.items()
            },
        }

        return render(request, "home.html", context)
