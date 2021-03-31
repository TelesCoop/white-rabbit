import datetime
from collections import Counter
from datetime import date
from typing import List, Dict, Counter as TypingCounter

from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.views import View
from jours_feries_france import JoursFeries

from .constants import MIN_WORKING_HOURS_FOR_FULL_DAY, DEFAULT_DAY_WORKING_HOURS
from .events import (
    Event,
    EventsPerEmployee,
    group_events_by_day,
    get_all_events_per_employee,
)
from .models import Employee
from .state_of_day import (
    state_of_days,
    state_of_days_per_employee_for_week,
)


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


def time_per_project_per_employee(events_per_employee: EventsPerEmployee) -> dict:
    """Counts the number of days spent per project."""
    to_return: TypingCounter[str] = Counter()
    for _, employee_events in events_per_employee.items():
        to_return.update(time_per_project(employee_events))

    return dict(to_return)


def time_per_project(events: List[Event]) -> TypingCounter[str]:
    to_return: TypingCounter[str] = Counter()
    for _, events_for_day in group_events_by_day(events).items():
        distribution = day_distribution(events_for_day)
        for name, duration in distribution.items():
            to_return[name] += duration  # type: ignore
    return to_return


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
        ]
        events_per_employee: EventsPerEmployee = get_all_events_per_employee()

        today = datetime.date.today()
        start_of_next_week = today - datetime.timedelta(days=today.weekday())
        start_of_next_month = today.replace(day=1) + relativedelta(month=1)
        end_of_next_month = (
            start_of_next_month + relativedelta(month=1) - relativedelta(days=1)
        )
        end_of_next_week = start_of_next_week + datetime.timedelta(days=4)

        context = {
            "events": events_per_employee,
            "employees": employees,
            "time_per_project": time_per_project_per_employee(events_per_employee),
            "curent_week_state": state_of_days_per_employee_for_week(
                events_per_employee, today
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