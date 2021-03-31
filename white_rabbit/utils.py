import datetime
from typing import Union


def start_of_day(d) -> Union[datetime.date, datetime.datetime]:
    """Returns start of day."""
    if isinstance(d, datetime.date):
        return d
    return datetime.datetime(d.year, d.month, d.day)
