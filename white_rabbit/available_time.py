import datetime
from typing import Iterable

from jours_feries_france import JoursFeries

from white_rabbit.constants import MIN_WORKING_HOURS_FOR_FULL_DAY
from white_rabbit.events import group_events_by_day
from white_rabbit.models import Employee
from white_rabbit.typing import Event


def available_time_of_employee(
        employee: Employee, events: Iterable[Event], start_date: datetime.date, end_date: datetime.date
):
    """
    Returns the number of working days that are available for an employee.

    Note: days in the past cannot be available.
    """
    events_per_day = group_events_by_day(events)
    availability_duration = 0
    today = datetime.date.today()

    day = start_date - datetime.timedelta(days=1)
    while day < end_date:
        day += datetime.timedelta(days=1)

        if day < today:
            continue

        # for weekend and blank holiday
        if day.weekday() >= 5 or JoursFeries.is_bank_holiday(day, zone="Métropole"):
            continue

        busy_duration = sum(event["duration"] for event in events_per_day.get(day, []))
        if busy_duration >= MIN_WORKING_HOURS_FOR_FULL_DAY:
            continue

        availability_duration += (
                max(employee.default_day_working_hours - busy_duration, 0)
                / employee.default_day_working_hours
        )

    return availability_duration