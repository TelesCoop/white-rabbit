from typing import List, TypedDict, Dict, Iterable, Union
import datetime

from white_rabbit.models import Employee


class ProjectDetail(TypedDict):
    employee: str
    date: datetime.date
    duration: float


class ProjectDistribution(TypedDict):
    duration: float
    detail_name: Union[str, int, None]


class ProjectTime(TypedDict):
    duration: float
    subprojects: dict
    events: List[ProjectDetail]


class MonthDetail(TypedDict):
    order: List[int]
    values: Dict[int, ProjectTime]


class Event(TypedDict):
    project_id: int
    project_name: str
    name: str
    subproject_name: Union[str, None]
    duration: float
    start_datetime: datetime.date
    end_datetime: datetime.date
    category: str


AllProjectClient = List[Dict[str, float]]
EventsPerEmployee = Dict[Employee, Iterable[Event]]
MonthDetailPerEmployeePerMonth = Dict[str, Dict[str, MonthDetail]]
