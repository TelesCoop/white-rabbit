
from typing import List, TypedDict, Dict, Iterable, Union
import datetime

from white_rabbit.models import Employee


class ProjectDetail(TypedDict):
    employee: str
    date: datetime.date
    duration: float


class ProjectDistribution(TypedDict):
    duration: float
    subproject_name: Union[str, None]


class ProjectTime(TypedDict):
    duration: float
    subprojects: dict
    events: List[ProjectDetail]


class MonthDetail(TypedDict):
    order: List[int]
    values: Dict[int, ProjectTime]


class Event(TypedDict):
    project_id: int
    name: str
    subproject_name: Union[str, None]
    duration: float
    day: datetime.date


AllProjectClient = List[Dict[str, float]]
EventsPerEmployee = Dict[Employee, Iterable[Event]]
MonthDetailPerEmployeePerMonth = Dict[str, Dict[str, MonthDetail]]
