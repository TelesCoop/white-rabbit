import datetime
from collections import defaultdict
from itertools import groupby

from typing import Union, Iterable, Dict, Any

from dateutil.relativedelta import relativedelta

from white_rabbit.constants import DEFAULT_DAY_WORKING_HOURS
from white_rabbit.models import Employee
from white_rabbit.typing import Event, ProjectDistribution


def start_of_day(d) -> Union[datetime.date, datetime.datetime]:
    """Returns start of day."""
    if isinstance(d, datetime.date):
        return d
    return datetime.datetime(d.year, d.month, d.day)


def convert_duration_to_work_hours_and_minutes(duration: float) -> str:
    # Convert duration to work hours
    duration_in_work_hours = duration * DEFAULT_DAY_WORKING_HOURS

    # Separate the whole hours and the fractional part (which represents the minutes)
    hours = int(duration_in_work_hours)
    minutes = (duration_in_work_hours - hours) * 60

    # Round the minutes to the nearest whole number
    minutes = round(minutes)
    if minutes == 0:
        minutes = ""
    return f"({hours}h{minutes})"


def calculate_days_spent(duration, divider):
    days_spent = duration / divider
    if days_spent > 1:
        days_spent = 1
    return days_spent


def calculate_period_start(period_index, time_period="month"):
    today = datetime.date.today()
    days_delta = today.day - 1 if time_period == "month" else today.weekday()
    start_of_current_period = today - datetime.timedelta(days=days_delta)
    return start_of_current_period + relativedelta(**{f"{time_period}s": period_index})


def calculate_period_start(period_index, time_period="month", time_shift_direction="future"):
    today = datetime.date.today()
    days_delta = today.day - 1 if time_period == "month" else today.weekday()
    start_of_current_period = today - datetime.timedelta(days=days_delta)

    if time_shift_direction == "future":
        return start_of_current_period + relativedelta(**{f"{time_period}s": period_index})
    elif time_shift_direction == "past":
        return start_of_current_period - relativedelta(**{f"{time_period}s": period_index})
    else:
        raise ValueError("Invalid time_shift_direction. Choose either 'past' or 'future'.")


def calculate_period_key(period, time_period="month"):
    if time_period == "month":
        return f"{period.month}/{period.year}"
    else:
        return period.isocalendar()[1]


def count_number_days_spent_per_project(
        events: Iterable[Event],
        employee: Employee
) -> Dict[int, ProjectDistribution]:
    """
    Given all events for a day for an employee, count the number of days
    (<= 1) spent on each project.
    """
    if getattr(employee, "default_day_working_hours") is None:
        divider = float(employee.default_day_working_hours)
    else:
        divider = float(employee.min_working_hours_for_full_day)

    project_time_distribution: Dict[int, ProjectDistribution] = defaultdict(
        lambda: {"days_spent": 0.0, "subproject_name": "", "duration": 0.0}
    )
    for event in events:
        project_time_distribution[event["project_id"]]["subproject_name"] = event["subproject_name"]
        project_time_distribution[event["project_id"]]["days_spent"] += calculate_days_spent(event["duration"], divider)
        project_time_distribution[event["project_id"]]["duration"] += event["duration"]

    return dict(project_time_distribution)


def group_events_by_day(
        events: Iterable[Event],
) -> Dict[datetime.date, Iterable[Event]]:
    """Returns a dict day -> events for day."""
    return {k: list(g) for k, g in groupby(events, lambda event: event["start_datetime"].date() if isinstance(
        event["start_datetime"], datetime.datetime) else event["start_datetime"])}


def generate_time_periods(n_periods: int, time_period: str = "month"):
    periods: Any = []
    for period_index in range(n_periods):
        period_start = calculate_period_start(period_index, time_period)
        if time_period == "month":
            period_key = f"{period_start.month}/{period_start.year}"
            end_of_period = None
        else:
            period_key = f"{period_start.isocalendar()[1]}"
            end_of_period = period_start + datetime.timedelta(days=6)

        periods.append({"key": period_key, "start": period_start, "end": end_of_period})

    return periods
