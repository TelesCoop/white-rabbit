import datetime
from collections import defaultdict
from itertools import groupby

from typing import Union, Iterable, Dict, Any, Callable

from dateutil.relativedelta import relativedelta

from white_rabbit.constants import DEFAULT_MIN_WORKING_HOURS

from white_rabbit.typing import Event, ProjectDistribution


def start_of_day(d) -> Union[datetime.date, datetime.datetime]:
    """Returns start of day."""
    if isinstance(d, datetime.date):
        return d
    return datetime.datetime(d.year, d.month, d.day)


def convert_duration_to_work_hours_and_minutes(duration: float) -> str:
    duration_in_work_hours = duration * DEFAULT_MIN_WORKING_HOURS

    hours = int(duration_in_work_hours)
    minutes = (duration_in_work_hours - hours) * 60

    minutes = round(minutes)
    if minutes == 0:
        minutes = ""
    return f"({hours}h{minutes})"


def convert_duration_to_days_spent(duration, divider):
    if not isinstance(divider, float):
        divider = float(divider)

    days_spent = duration / divider
    if days_spent > 1:
        days_spent = 1
    return days_spent


def calculate_period_start(
    period_index, time_period="month", time_shift_direction="future"
):
    today = datetime.date.today()
    days_delta = today.day - 1 if time_period == "month" else today.weekday()
    start_of_current_period = today - datetime.timedelta(days=days_delta)

    if time_shift_direction == "future":
        return start_of_current_period + relativedelta(
            **{f"{time_period}s": period_index}
        )
    elif time_shift_direction == "past":
        return start_of_current_period - relativedelta(
            **{f"{time_period}s": period_index}
        )
    else:
        raise ValueError(
            "Invalid time_shift_direction. Choose either 'past' or 'future'."
        )


def calculate_period_key(period, time_period="month"):
    if time_period == "month":
        return f"{period.month}-{period.year}"
    else:
        return period.isocalendar()[1]


def count_number_days_spent(
    events: Iterable[Event],
    key_func: Callable[[Event], int],
    min_working_hours_for_full_day: int = DEFAULT_MIN_WORKING_HOURS,
) -> Dict[int, ProjectDistribution]:
    grouped_projects: Dict[int, Dict] = defaultdict(
        lambda: {"days_spent": 0.0, "duration": 0.0, "category": "", "events": []}
    )
    for event in events:
        key = key_func(event)
        grouped_projects[key]["days_spent"] += convert_duration_to_days_spent(
            event["duration"], min_working_hours_for_full_day
        )
        grouped_projects[key]["duration"] += event["duration"]
        grouped_projects[key]["events"].append(event)

    return dict(grouped_projects)


def day_distribution(
    events: Iterable[Event], employee
) -> Dict[int, ProjectDistribution]:
    """
    Given all events for a day for an employee, count the number of days
    (<= 1) spent on each project.
    """
    from white_rabbit.models import Employee

    employee: Employee
    total_time = sum(event["duration"] for event in events)
    is_full_day = total_time >= employee.min_working_hours_for_full_day
    if is_full_day:
        divider = total_time
    else:
        divider = float(employee.default_day_working_hours)

    distribution: Dict[int, ProjectDistribution] = defaultdict(
        lambda: {"duration": 0.0, "subproject_name": ""}
    )

    for event in events:
        distribution[event["project_id"]]["subproject_name"] = event["subproject_name"]
        distribution[event["project_id"]]["duration"] += event["duration"] / divider

    return dict(distribution)


# def count_number_days_spent_per_project(
#     events: Iterable[Event],
#     min_working_hours_for_full_day: int = DEFAULT_MIN_WORKING_HOURS,
# ) -> Dict[int, ProjectDistribution]:
#     return count_number_days_spent(
#         events,
#         key_func=lambda event: event["project_id"],
#         min_working_hours_for_full_day=min_working_hours_for_full_day,
#     )


def is_date_same_or_after_today(date: datetime.date) -> bool:
    if isinstance(date, datetime.datetime):
        date = date.date()
    return date >= datetime.date.today()


def events_per_day(
    events: Iterable[Event], start_datetime: datetime.date, end_datetime: datetime.date
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
        day = start_datetime + datetime.timedelta(days=i)
        if day not in to_return:
            to_return[day] = []

    return to_return


def count_number_days_spent_per_project_category(
    events: Iterable[Event], min_working_hours_for_full_day: int = None
) -> Dict[int, ProjectDistribution]:
    return count_number_days_spent(
        events,
        key_func=lambda event: event["category"],
        min_working_hours_for_full_day=min_working_hours_for_full_day,
    )


def filter_events_per_time_period(
    events, timeperiod: datetime.datetime = None, timeperiod_type: str = "month"
):
    if timeperiod is None:
        return events
    if timeperiod_type == "month":
        return [
            event
            for event in events
            if event["start_datetime"].month == timeperiod.month
            and event["start_datetime"].year == timeperiod.year
        ]
    elif timeperiod_type == "week":
        return [
            event
            for event in events
            if event["start_datetime"].isocalendar()[1] == timeperiod.isocalendar()[1]
            and event["start_datetime"].year == timeperiod.year
        ]
    elif timeperiod_type == "day":
        events = []
        for event in events:
            is_datetime = isinstance(event["start_datetime"], datetime.datetime)
            event_date = event["start_datetime"]
            if is_datetime:
                event_date = event_date.date()
            if event_date == timeperiod:
                events.append(event)
        return events
    else:
        raise ValueError("Invalid timeperiod_type. Choose either 'month' or 'week'.")


def group_events_per_category(events):
    """Returns a dict category -> events for category."""
    return {k: list(g) for k, g in groupby(events, lambda event: event["category"])}


def group_events_by_day(
    events: Iterable[Event],
) -> Dict[datetime.date, Iterable[Event]]:
    """Returns a dict day -> events for day."""
    return {
        k: list(g)
        for k, g in groupby(
            events,
            lambda event: event["start_datetime"].date()
            if isinstance(event["start_datetime"], datetime.datetime)
            else event["start_datetime"],
        )
    }


def generate_time_periods(
    n_periods: int, time_period: str = "month", time_shift_direction: str = "future"
):
    periods: Any = []
    for period_index in range(n_periods):
        period_start = calculate_period_start(
            period_index, time_period, time_shift_direction
        )
        if time_period == "month":
            period_key = f"{period_start.month}-{period_start.year}"
            end_of_period = (
                period_start
                + relativedelta(**{f"{time_period}s": 1})  # type: ignore
                - relativedelta(days=1)
            )
        else:
            period_key = f"{period_start.isocalendar()[1]}"
            end_of_period = period_start + datetime.timedelta(days=6)

        periods.append({"key": period_key, "start": period_start, "end": end_of_period})

    return periods


def generate_time_periods_with_total(
    n_periods: int, time_period: str = "month", time_shift_direction: str = "future"
):
    periods = generate_time_periods(n_periods, time_period, time_shift_direction)
    periods.insert(
        0, {"key": "total", "start": periods[0]["start"], "end": periods[-1]["end"]}
    )
    return periods


def get_or_create_project(projects, project_id, project_detail):
    if project_id not in projects:
        projects[project_id] = {
            "total_duration": project_detail.total_duration,
            "total_days": project_detail.days_spent,
            "events": {},
        }
    else:
        projects[project_id]["total_duration"] += project_detail.total_duration
        projects[project_id]["total_days"] += project_detail.days_spent

    return projects[project_id]


def get_or_create_project_by_employee_and_category(
    projects, category, employee, project_detail
):
    if employee not in projects:
        projects[employee] = {}
    if category not in projects[employee]:
        projects[employee][category] = {"duration": 0, "days": 0, "events": []}

    projects[employee][category]["duration"] += project_detail.total_duration
    projects[employee][category]["days"] += project_detail.days_spent
    projects[employee][category]["events"].append(*project_detail.events)

    return projects


def get_or_create_employee_event(employees_events, employee_name, project_detail):
    if employee_name not in employees_events:
        employees_events[employee_name] = {
            "days_spent": project_detail.days_spent,
            "total_duration": project_detail.total_duration,
            "events": project_detail.events,
        }
    else:
        employees_events[employee_name]["days_spent"] += project_detail.days_spent
        employees_events[employee_name][
            "total_duration"
        ] += project_detail.total_duration
        employees_events[employee_name]["events"] += project_detail.events
    return employees_events[employee_name]
