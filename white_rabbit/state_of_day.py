import datetime
from collections import defaultdict
from datetime import date
from typing import Dict, Any, Iterable, DefaultDict

from white_rabbit.constants import DayState, DayStateDisplay
from white_rabbit.events import Event, EventsPerEmployee, events_per_day
from white_rabbit.models import Employee


def state_of_days_per_employee(
        events_per_employee: EventsPerEmployee,
        start_datetime: date,
        end_datetime: date,
        employees: Iterable[Employee] = None,
) -> Dict[datetime.date, Dict[Employee, Dict[str, Any]]]:
    """
    Returns a dict date -> (employee -> state of day) for each
    combination, including days without events.
    """
    if employees is None:
        # by default, we take all employees for which we have data,
        # but we might want to restrict to only some employees
        employees = list(events_per_employee)

    to_return: Dict[datetime.date, Dict[Employee, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict()
    )
    for employee in employees:
        employee_events = events_per_employee[employee]
        per_day_events = events_per_day(employee_events, start_datetime, end_datetime)
        for day, events in per_day_events.items():
            day_to_return = day.strftime("%Y-%m-%d")
            to_return[day_to_return][employee.name] = {
                "state": state_of_day(events, employee=employee),
                "events": events,
            }

    return dict(to_return)


def state_of_days(
        employee: Employee, events: Iterable[Event], start_datetime: date, end_datetime: date
) -> Dict[datetime.date, Dict[str, Any]]:
    """
    Returns a dict date -> (employee -> state of day) for each
    combination, including days without events.
    """
    to_return: DefaultDict[datetime.date, Dict[str, Any]] = defaultdict()
    per_day_events = events_per_day(events, start_datetime, end_datetime)
    for day, events_for_day in per_day_events.items():
        day_to_return = day.strftime("%Y-%m-%d")
        to_return[day_to_return] = {
            "state": state_of_day(events_for_day, employee=employee),
            "display_state": state_of_day(
                events_for_day, employee=employee, display=True
            ),
            "events": events_for_day,
        }

    return dict(to_return)


def state_of_days_per_employee_for_week(
        events_per_employee: EventsPerEmployee,
        day: datetime.date = None,
        employees: Iterable[Employee] = None,
) -> Dict[datetime.date, Dict[Employee, Dict[str, Any]]]:
    if day is None:
        day = datetime.date.today()
    start_of_week = day - datetime.timedelta(days=day.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=4)
    return state_of_days_per_employee(
        events_per_employee, start_of_week, end_of_week, employees
    )


def state_of_days_for_week(
        events: Iterable[Event], employee: Employee, day: datetime.date = None
) -> Dict[datetime.date, Dict[str, Any]]:
    if day is None:
        day = datetime.date.today()
    start_of_week = day - datetime.timedelta(days=day.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return state_of_days(employee, events, start_of_week, end_of_week)


def state_of_day(events: Iterable[Event], employee: Employee, display=False) -> str:
    """Returns the state of a day as a string."""
    if not events:
        if display:
            return DayStateDisplay.empty
        return DayState.empty
    total_duration = sum(event["duration"] for event in events)
    if not total_duration:
        if display:
            return DayStateDisplay.empty
        return DayState.empty
    if total_duration < employee.min_working_hours_for_full_day:
        if display:
            return DayStateDisplay.incomplete.format(
                total_duration,
                float(employee.min_working_hours_for_full_day) - total_duration,
            )
        return DayState.incomplete
    if display:
        return DayStateDisplay.complete.format(total_duration)
    return DayState.complete
