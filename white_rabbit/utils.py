import datetime
from collections import defaultdict
from itertools import groupby

from typing import Union, Iterable, Dict, Any, Callable, NamedTuple

from dateutil.relativedelta import relativedelta

from white_rabbit.constants import DEFAULT_MIN_WORKING_HOURS

from white_rabbit.typing import Event, ProjectDistribution


class Period(NamedTuple):
    key: str
    start: datetime.date
    end: datetime.date


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
    events: Iterable[Event],
    employee,
    group_by: str = "project",
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

    distribution: Dict[Union[str, int], ProjectDistribution] = defaultdict(
        lambda: {"duration": 0.0, "subproject_name": ""}
    )

    for event in events:
        if group_by == "project":
            # TODO if multiple events for the same day have different subproject,
            #  this will count everything as the last one
            distribution[event["project_id"]]["detail_name"] = event["subproject_name"]
            distribution[event["project_id"]]["duration"] += event["duration"] / divider
        elif group_by == "category":
            distribution[event["category"]]["detail_name"] = event["project_id"]
            distribution[event["category"]]["duration"] += event["duration"] / divider
    return dict(distribution)


def is_date_same_or_after_today(date: datetime.date) -> bool:
    if isinstance(date, datetime.datetime):
        date = date.date()
    return date >= datetime.date.today()


def convert_to_datetime_if_date(date: Union[datetime.date, datetime.datetime]):
    if isinstance(date, datetime.date):
        return datetime.datetime(date.year, date.month, date.day)
    return date


def is_event_between_dates(event_datetime, start_datetime, end_datetime):
    if isinstance(start_datetime, datetime.date):
        start_datetime = convert_to_datetime_if_date(start_datetime)
    if isinstance(end_datetime, datetime.date):
        end_datetime = convert_to_datetime_if_date(end_datetime)
    if isinstance(event_datetime, datetime.date):
        event_datetime = convert_to_datetime_if_date(event_datetime)
    return start_datetime <= event_datetime <= end_datetime


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
        if is_event_between_dates(event["start_datetime"], start_datetime, end_datetime)
    ]
    to_return = group_events_by_day(events)

    # also include days without events
    for i in range(delta.days + 1):
        day = start_datetime + datetime.timedelta(days=i)
        if day not in to_return:
            to_return[day] = []

    return to_return


def filter_todo_or_done(events, key: str):
    if not key:
        return events
    if key.endswith("todo"):
        return [event for event in events if not is_before_today(event["end_datetime"])]
    elif key.endswith("done"):
        return [event for event in events if is_before_today(event["end_datetime"])]
    return events


def filter_events_per_time_period(
    events,
    timeperiod: datetime.datetime = None,
    timeperiod_type: str = "month",
    period_key=None,
):
    events = filter_todo_or_done(events, period_key)
    if timeperiod_type == "year":
        return [
            event for event in events if event["start_datetime"].year == timeperiod.year
        ]
    if period_key and is_total_key(period_key):
        return events
    if timeperiod is None:
        return events
    if timeperiod_type == "month":
        return [
            event
            for event in events
            if event["start_datetime"].month == timeperiod.month
            and event["start_datetime"].year == timeperiod.year
        ]
    if timeperiod_type == "week":
        return [
            event
            for event in events
            if event["start_datetime"].isocalendar()[1] == timeperiod.isocalendar()[1]
            and event["start_datetime"].year == timeperiod.year
        ]
    if timeperiod_type == "day":
        events = []
        for event in events:
            is_datetime = isinstance(event["start_datetime"], datetime.datetime)
            event_date = event["start_datetime"]
            if is_datetime:
                event_date = event_date.date()
            if event_date == timeperiod:
                events.append(event)
        return events

    raise ValueError("Invalid timeperiod_type. Choose 'month', 'week' or 'year'")


def group_events_per_category(events):
    """Returns a dict category -> events for category."""
    return {k: list(g) for k, g in groupby(events, lambda event: event["category"])}


def is_before_today(date: Union[datetime.date, datetime.datetime]) -> bool:
    if isinstance(date, datetime.datetime):
        date = date.date()
    return date < datetime.date.today()


def group_events_by_day(
    events: Iterable[Event],
) -> Dict[datetime.date, Iterable[Event]]:
    """Returns a dict day -> events for day."""
    return {
        k: list(g)
        for k, g in groupby(
            events,
            lambda event: (
                event["start_datetime"].date()
                if isinstance(event["start_datetime"], datetime.datetime)
                else event["start_datetime"]
            ),
        )
    }


def time_period_for_month(month: str) -> Period:
    """Given a month in the format YYYY-MM, returns a dict with the start and end dates."""
    month, year = month.split("-")
    return {
        "key": f"{month}-{year}",
        "start": datetime.date(int(year), int(month), 1),
        "end": datetime.date(int(year), int(month), 1)
        + relativedelta(months=1)
        - relativedelta(days=1),
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
            period_key = period_start.strftime("%m-%Y")
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
    current_year = datetime.date.today().year
    year_periods = [
        {
            "key": f"total-{current_year}-todo",
            "label": f"Prévu {current_year}",
            "is_total": True,
        },
        {
            "key": f"total-{current_year}-done",
            "label": f"Effectué {current_year}",
            "is_total": True,
        },
    ] + [
        {"key": f"total-{year}", "label": f"Total {year}", "is_total": True}
        for year in range(current_year, 2020, -1)
    ]
    total_periods = [
        {"key": "total", "label": "Total", "is_total": True},
        {"key": "total_done", "label": "Total effectué", "is_total": True},
        {"key": "total_todo", "label": "Total prévu", "is_total": True},
    ]
    time_periods = generate_time_periods(n_periods, time_period, time_shift_direction)

    return {
        "total_periods": total_periods + year_periods,
        "time_periods": time_periods,
    }


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


def is_total_key(key: str) -> bool:
    return key.startswith("total")


def is_year_key(key: str) -> bool:
    return key.startswith("total-")
