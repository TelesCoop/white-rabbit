from dataclasses import dataclass

DEFAULT_DAY_WORKING_HOURS = 8
MIN_WORKING_HOURS_FOR_FULL_DAY = 6
ALIASES = {
    "Aides Jeunes": ["aides jeunes", ],
    "Démocratie Ouverte": ["do", "démocratie ouverte"],
    "Green Menu": ["green menu", "green-menu"],
    "Oklm": ["oklm", "journée oklm"],
    "Présentiel": ["présentielle", "présentiel", "réunion présentielle"],
    "Vie d'équipe": ["vie d'équipe", "équipe", "vie d'equipe"],
    "Jour férié": ["jour férier", "férier"],
    "Zoon": ["zoon", "la zone"],
    "Site Internet": ["site internet", "site vitrine"],
    "Planification": ["planification", "planning"],
    "Commercial": ["commercial", "propale"],
}


@dataclass
class DayState:
    empty = "empty"
    incomplete = "incomplete"
    complete = "complete"
