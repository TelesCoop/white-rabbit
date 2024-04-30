import datetime
from collections import defaultdict
from itertools import groupby

from typing import Union, Iterable, Dict, Any, Callable

from dateutil.relativedelta import relativedelta

from white_rabbit.constants import DEFAULT_DAY_WORKING_HOURS
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectFinder
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
        return f"{period.month}-{period.year}"
    else:
        return period.isocalendar()[1]


def count_number_days_spent(
        events: Iterable[Event],
        employee: Employee,
        key_func: Callable[[Event], int]
) -> Dict[int, ProjectDistribution]:
    divider = float(employee.default_day_working_hours) if getattr(employee,
                                                                   "default_day_working_hours") is not None else float(
        employee.min_working_hours_for_full_day)

    project_time_distribution: Dict[int, Dict] = defaultdict(
        lambda: {"days_spent": 0.0, "duration": 0.0, "category": "", "projects": []}
    )
    for event in events:
        key = key_func(event)
        project_time_distribution[key]["days_spent"] += calculate_days_spent(event["duration"], divider)
        project_time_distribution[key]["duration"] += event["duration"]
        project_time_distribution[key]["projects"].append(event)

    return dict(project_time_distribution)


def count_number_days_spent_per_project(
        events: Iterable[Event],
        employee: Employee
) -> Dict[int, ProjectDistribution]:
    return count_number_days_spent(events, employee, key_func=lambda event: event["project_id"])


def count_number_days_spent_per_project_category(
        events: Iterable[Event],
        employee: Employee
) -> Dict[int, ProjectDistribution]:
    return count_number_days_spent(events, employee, key_func=lambda event: event["category"])


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
            period_key = f"{period_start.month}-{period_start.year}"
            end_of_period = None
        else:
            period_key = f"{period_start.isocalendar()[1]}"
            end_of_period = period_start + datetime.timedelta(days=6)

        periods.append({"key": period_key, "start": period_start, "end": end_of_period})

    return periods


def get_or_create_project(projects, project_id, project_detail):
    if project_id not in projects:
        projects[project_id] = {
            "total_duration": project_detail.total_duration,
            "total_days": project_detail.days_spent,
            "employees_events": {}
        }
    else:
        projects[project_id]["total_duration"] += project_detail.total_duration
        projects[project_id]["total_days"] += project_detail.days_spent

    return projects[project_id]


def get_or_create_project_by_employee_and_category(projects, category, employee, project_detail):
    if employee not in projects:
        projects[employee] = {}
    if category not in projects[employee]:
        projects[employee][category] = {
            "total_duration": 0,
            "total_days": 0,
            "events": None
        }

    projects[employee][category]["total_duration"] += project_detail.total_duration
    projects[employee][category]["total_days"] += project_detail.days_spent
    projects[employee][category]["events"] = project_detail.events

    return projects


def get_or_create_employee_event(employees_events, employee_name, project_detail):
    if employee_name not in employees_events:
        employees_events[employee_name] = {
            "days_spent": project_detail.days_spent,
            "total_duration": project_detail.total_duration,
            "events": project_detail.events
        }
    else:
        employees_events[employee_name]["days_spent"] += project_detail.days_spent
        employees_events[employee_name]["total_duration"] += project_detail.total_duration
        employees_events[employee_name]["events"] += project_detail.events
    return employees_events[employee_name]
