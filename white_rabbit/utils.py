import datetime

from typing import Union

from white_rabbit.constants import DEFAULT_DAY_WORKING_HOURS


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

def convert_duration_to_work_day(duration: float) -> str:
    # Convert duration to work days
    duration_in_work_days = duration / DEFAULT_DAY_WORKING_HOURS

    # Round the days to the nearest whole number
    days = round(duration_in_work_days)

    return f"{days} jours"
