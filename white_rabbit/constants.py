from dataclasses import dataclass

DEFAULT_DAY_WORKING_HOURS = 8
MIN_WORKING_HOURS_FOR_FULL_DAY = 6


@dataclass
class DayState:
    empty = "empty"
    incomplete = "incomplete"
    complete = "complete"
