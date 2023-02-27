import datetime
import json
from collections import Counter, defaultdict
from datetime import date
from typing import (
    Dict,
    Any,
    Iterable,
    List,
    DefaultDict,
    TypedDict,
    Union,
)

from dateutil.relativedelta import relativedelta
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from jours_feries_france import JoursFeries

from .constants import MIN_WORKING_HOURS_FOR_FULL_DAY
from .events import (
    Event,
    EventsPerEmployee,
    group_events_by_day,
    get_events_for_employees,
    employees_for_user,
)
from .models import Employee, Project, Company
from .project_name_finder import ProjectNameFinder
from .state_of_day import (
    state_of_days_per_employee_for_week,
)


class MyLoginView(LoginView):
    template_name = "admin/login.html"


class ProjectDistribution(TypedDict):
    duration: float
    subproject_name: Union[str, None]


def day_distribution(
    events: Iterable[Event], employee: Employee
) -> Dict[int, ProjectDistribution]:
    """
    Given all events for a day for an employee, count the number of days
    (<= 1) spent on each project.
    """
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


def upcoming_time(
    events_per_employee: EventsPerEmployee, employees: List[Employee], time_period: str
):
    if time_period not in ["week", "month"]:
        raise NotImplementedError("time_period must be one of week, month")

    is_month_period = time_period == "month"

    n_upcoming_periods = 12
    today = datetime.date.today()
    if is_month_period:
        days_delta = today.day - 1
        return_key = "month_names"

    else:
        days_delta = today.weekday()
        return_key = "weeks"
    start_of_current_period = today - datetime.timedelta(days=days_delta)

    if employees is None:
        employees = list(events_per_employee)

    to_return: Any = {
        return_key: [],
        "employees": list(employee.name for employee in employees),
    }
    for period_index in range(n_upcoming_periods):
        period_start = start_of_current_period + relativedelta(
            **{f"{time_period}s": period_index}  # type: ignore
        )
        if is_month_period:
            to_return[return_key].append(period_start.strftime("%b"))
        else:
            end_of_period = period_start + datetime.timedelta(days=6)
            period_start_number = period_start.isocalendar()[1]
            to_return[return_key].append(
                {
                    "number": period_start_number,
                    "start": f"{period_start.day}/{period_start.month}",
                    "end": f"{end_of_period.day}/{end_of_period.month}",
                }
            )

    # total for each project for each employee
    projects_total: DefaultDict = defaultdict(Counter)

    for employee, employee_events in events_per_employee.items():
        to_return[employee.name] = {}
        for period_index in range(n_upcoming_periods):
            period_start = start_of_current_period + relativedelta(
                **{f"{time_period}s": period_index}  # type: ignore
            )
            period_end = (
                period_start
                + relativedelta(**{f"{time_period}s": 1})  # type: ignore
                - relativedelta(days=1)
            )
            if is_month_period:
                period_key = period_start.strftime("%b")
            else:
                period_key = period_start.isocalendar()[1]  # type: ignore

            projects = month_detail_per_employee_per_month(
                {employee: employee_events}, **{time_period: period_start}
            )["Total"]["Total"]["values"]
            for project_id, project_data in projects.items():
                projects_total[employee][project_id] += project_data["duration"]

            to_return[employee.name][period_key] = {
                "availability": available_time_of_employee(
                    employee, employee_events, period_start, period_end
                ),
                "projects": projects,
            }
        to_return[employee.name]["projects_total"] = [
            proj[0] for proj in projects_total[employee].most_common()
        ]

    return to_return


class ProjectDetail(TypedDict):
    employee: str
    date: datetime.date
    duration: float


class ProjectTime(TypedDict):
    duration: float
    subprojects: dict
    events: List[ProjectDetail]


class MonthDetail(TypedDict):
    order: List[int]
    values: Dict[int, ProjectTime]


MonthDetailPerEmployeePerMonth = Dict[str, Dict[str, MonthDetail]]


def month_detail_per_employee_per_month(  # noqa: C901
    events_per_employee: EventsPerEmployee,
    month: datetime.date = None,
    week: datetime.date = None,
) -> MonthDetailPerEmployeePerMonth:
    """
    Counts the number of days spent per project for selected month or week.

    If week and month are None, counts the historical total.
    """
    to_return_1: Dict[str, Dict[str, Dict[int, ProjectTime]]] = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: {
                    "duration": 0.0,
                    "events": [],
                    "subprojects": defaultdict(lambda: {"duration": 0.0}),
                }
            )
        )
    )
    # make sure specific keys exist and are at the start
    to_return_1["Total"]["Total"]  # noqa
    to_return_1["Total"]["Total effectué"]  # noqa
    to_return_1["Total"]["Total à venir"]  # noqa

    for employee, employee_events in events_per_employee.items():
        for event_date, events_for_day in group_events_by_day(employee_events).items():
            if month and (event_date.month, event_date.year) != (
                month.month,
                month.year,
            ):
                continue
            if week and (event_date.isocalendar()[:2] != week.isocalendar()[:2]):
                continue

            # format : YY-MM
            month_label = f"{event_date.strftime('%b %y')}"

            distribution: Dict[int, ProjectDistribution] = day_distribution(
                events_for_day, employee=employee
            )

            date_keys_to_update = ["Total", month_label]
            if event_date <= datetime.date.today():
                date_keys_to_update.append("Total effectué")
            else:
                date_keys_to_update.append("Total à venir")

            for project_id, details in distribution.items():
                # add both to total and relevant employee
                duration = details["duration"]  # type: ignore
                subproject_name = details["subproject_name"]  # type: ignore
                for employee_key in ["Total", employee.name]:
                    # add values both to total and relevant month
                    for date_key in date_keys_to_update:
                        to_return_1[employee_key][date_key][project_id][
                            "duration"
                        ] += duration
                        if subproject_name:
                            to_return_1[employee_key][date_key][project_id][
                                "subprojects"
                            ][subproject_name]["duration"] += duration
                        to_return_1[employee_key][date_key][project_id][
                            "events"
                        ].append(
                            {
                                "employee": employee.name,
                                "date": event_date,
                                "duration": duration,
                            }
                        )

    to_return: MonthDetailPerEmployeePerMonth = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: {
                    "order": [],
                    "values": {
                        "duration": 0.0,
                        "events": [],
                        "subprojects": defaultdict(lambda: {"duration": 0.0}),
                    },
                }
            )
        )
    )

    # sort by total duration for each month and total and keep order
    for employee_key, employee_values in to_return_1.items():
        for display_month, time_per_project in employee_values.items():
            project_ids_ordered = sorted(
                time_per_project.keys(),
                key=lambda project_id: time_per_project[project_id]["duration"],
                reverse=True,
            )
            to_return[employee_key][display_month] = {
                "order": project_ids_ordered,
                "values": time_per_project,
            }

    return to_return


def available_time_of_employee(
    employee: Employee, events: Iterable[Event], start_date: date, end_date: date
):
    """
    Returns the number of working days that are available for an employee.

    Note: days in the past cannot be available.
    """
    events_per_day = group_events_by_day(events)
    availability_duration = 0
    today = datetime.date.today()

    day = start_date - datetime.timedelta(days=1)
    while day < end_date:
        day += datetime.timedelta(days=1)

        if day < today:
            continue

        # for weekend and bank holiday
        if day.weekday() >= 5 or JoursFeries.is_bank_holiday(day, zone="Métropole"):
            continue

        busy_duration = sum(event["duration"] for event in events_per_day.get(day, []))
        if busy_duration >= MIN_WORKING_HOURS_FOR_FULL_DAY:
            continue

        availability_duration += (
            max(employee.default_day_working_hours - busy_duration, 0)
            / employee.default_day_working_hours
        )

    return availability_duration


AllProjectClient = List[Dict[str, float]]


def client_projects_for_company(company: Company) -> List[Project]:
    return list(Project.objects.filter(is_client_project=True, company=company))


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user
        employees = employees_for_user(user)
        today = datetime.date.today()
        display_employees = [
            employee
            for employee in employees
            if not employee.end_time_tracking_on
            or employee.end_time_tracking_on > today
        ]
        project_name_finder = ProjectNameFinder()
        events_per_employee: EventsPerEmployee = get_events_for_employees(
            employees, project_name_finder, request=self.request
        )

        today = datetime.date.today()

        computed_month_detail_per_employee_per_month = (
            month_detail_per_employee_per_month(events_per_employee)
        )
        display_employee_names = {employee.name for employee in employees}
        # filter out employees we are not supposed to know about
        computed_month_detail_per_employee_per_month = {
            employee: employee_data
            for employee, employee_data in computed_month_detail_per_employee_per_month.items()
            if employee == "Total" or employee in display_employee_names
        }

        # get current month
        filled_month_list = list(
            computed_month_detail_per_employee_per_month["Total"].keys()
        )
        try:
            active_month = filled_month_list.index(today.strftime("%b %y"))
        except ValueError:
            active_month = len(filled_month_list)

        project_details = project_name_finder.projects_for_company(
            user.employee.company
        )

        client_projects = client_projects_for_company(user.employee.company)
        for project in client_projects:
            try:
                project.done = computed_month_detail_per_employee_per_month["Total"][
                    "Total"
                ]["values"][project.pk]["duration"]
            except KeyError:
                project.done = 0
            project.remaining = float(project.days_sold) - project.done

        return {
            "active_month": active_month,
            "today": datetime.date.today(),
            "events": events_per_employee,
            "employees": employees,
            "display_employees": display_employees,
            "month_detail_per_employee_per_month_str": json.dumps(
                computed_month_detail_per_employee_per_month,
                default=str,
            ),
            "past_week_state": state_of_days_per_employee_for_week(
                events_per_employee, today - datetime.timedelta(days=7)
            ),
            "curent_week_state": state_of_days_per_employee_for_week(
                events_per_employee, today, employees
            ),
            "upcoming_weeks_str": json.dumps(
                upcoming_time(events_per_employee, display_employees, "week"),
                default=str,
            ),
            "upcoming_months_str": json.dumps(
                upcoming_time(events_per_employee, display_employees, "month"),
                default=str,
            ),
            "client_projects": client_projects,
            "project_details_str": json.dumps(project_details),
            "project_details": project_details,
        }


class AliasView(TemplateView):
    template_name = "alias.html"

    def get_context_data(self, **kwargs):
        company = self.request.user.employee.company
        aliasesByProject = {}

        for project in Project.objects.filter(company=company).order_by("name"):
            aliasesByProject[project.name] = [
                alias.name for alias in project.aliases.all()
            ]
        return {"aliasesByProject": aliasesByProject}
