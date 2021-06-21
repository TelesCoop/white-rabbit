import datetime
from collections import defaultdict
from datetime import date
from typing import Dict, Any, Iterable, DefaultDict

from white_rabbit.constants import DayState
from white_rabbit.events import Event, EventsPerEmployee, events_per_day
from white_rabbit.models import Employee, Company


def state_of_days_per_employee(
    events_per_employee: EventsPerEmployee,
    company: Company,
    start_date: date,
    end_date: date,
) -> Dict[datetime.date, Dict[Employee, Dict[str, Any]]]:
    """
    Returns a dict date -> (employee -> state of day) for each
    combination, including days without events.
    """
    to_return: Dict[datetime.date, Dict[Employee, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict()
    )
    for employee, employee_events in events_per_employee.items():
        per_day_events = events_per_day(employee_events, start_date, end_date)
        for day, events in per_day_events.items():
            to_return[day][employee] = {
                "state": state_of_day(events, company=company),
                "events": events,
            }

    return dict(to_return)


def state_of_days(
    employee: Employee, events: Iterable[Event], start_date: date, end_date: date
) -> Dict[datetime.date, Dict[str, Any]]:
    """
    Returns a dict date -> (employee -> state of day) for each
    combination, including days without events.
    """
    to_return: DefaultDict[datetime.date, Dict[str, Any]] = defaultdict()
    per_day_events = events_per_day(events, start_date, end_date)
    for day, events_for_day in per_day_events.items():
        to_return[day] = {
            "state": state_of_day(events_for_day, company=employee.company),
            "events": events_for_day,
        }

    return dict(to_return)


def state_of_days_per_employee_for_week(
    events_per_employee: EventsPerEmployee, company: Company, day: datetime.date = None
) -> Dict[datetime.date, Dict[Employee, Dict[str, Any]]]:
    if day is None:
        day = datetime.date.today()
    start_of_week = day - datetime.timedelta(days=day.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=4)
    return state_of_days_per_employee(
        events_per_employee, company, start_of_week, end_of_week
    )


def state_of_days_for_week(
    events: Iterable[Event], employee: Employee, day: datetime.date = None
) -> Dict[datetime.date, Dict[str, Any]]:
    if day is None:
        day = datetime.date.today()
    start_of_week = day - datetime.timedelta(days=day.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=4)
    return state_of_days(employee, events, start_of_week, end_of_week)


# TODO delete
# def state_of_days(
#     events: List[Event], company: Company, start_date: date, end_date: date
# ):
#     per_day_events = events_per_day(events, start_date, end_date)
#     return {
#         day: state_of_day(events, company) for day, events in per_day_events.items()
#     }


def state_of_day(events: Iterable[Event], company: Company) -> str:
    """Returns the state of a day as a string."""
    if not events:
        return DayState.empty
    total_duration = sum(event["duration"] for event in events)
    if not total_duration:
        return DayState.empty
    if total_duration < company.min_working_hours_for_full_day:
        return DayState.incomplete
    return DayState.complete
