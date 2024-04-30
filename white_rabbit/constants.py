from dataclasses import dataclass

DEFAULT_NB_WORKING_HOURS = 8
DEFAULT_MIN_WORKING_HOURS = 6
DEFAULT_MAX_WORKING_HOURS = 10
DEFAULT_ROUND_DURATION_PRECISION = 2


@dataclass
class DayState:
    empty = "empty"
    incomplete = "incomplete"
    complete = "complete"


@dataclass
class DayStateDisplay:
    empty = "vide"
    incomplete = "incomplet - {:.1f} heures - manque {:.1f} heures"
    complete = "complet - {:.1f} heures"


@dataclass
class DayStateDisplay:
    empty = "vide"
    incomplete = "incomplet - {:.1f} heures - manque {:.1f} heures"
    complete = "complet - {:.1f} heures"
