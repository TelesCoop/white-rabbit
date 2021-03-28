import datetime
from collections import defaultdict
from datetime import date
from typing import Dict, List

from projects_dashboard.constants import DayState, MIN_WORKING_HOURS_FOR_FULL_DAY
from projects_dashboard.events import Event, EventsPerEmployee, events_per_day


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


def state_of_days_per_employee_for_week(
    events_per_employee: EventsPerEmployee, day: datetime.date = None
):
    if day is None:
        day = datetime.date.today()
    start_of_week = day - datetime.timedelta(days=day.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=4)
    return state_of_days_per_employee(events_per_employee, start_of_week, end_of_week)


def state_of_days(events: List[Event], start_date: date, end_date: date):
    per_day_events = events_per_day(events, start_date, end_date)
    return {day: state_of_day(events) for day, events in per_day_events.items()}


def state_of_day(events: List[Event]) -> str:
    """Returns the state of a day as a string."""
    if not events:
        return DayState.empty
    total_duration = sum(event["duration"] for event in events)
    if not total_duration:
        return DayState.empty
    if total_duration < MIN_WORKING_HOURS_FOR_FULL_DAY:
        return DayState.incomplete
    return DayState.complete
