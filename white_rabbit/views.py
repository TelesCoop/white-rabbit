import datetime
import json
from collections import Counter, defaultdict
from datetime import date
from typing import (
    Dict,
    Counter as TypingCounter,
    Any,
    Iterable,
    List,
    DefaultDict,
    TypedDict,
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
from .models import Employee
from .project_name_finder import ProjectNameFinder
from .state_of_day import (
    state_of_days_per_employee_for_week,
)


class MyLoginView(LoginView):
    template_name = "admin/login.html"


def day_distribution(events: Iterable[Event], employee: Employee) -> Dict[str, float]:
    """Given all events for a day for an employee, count the number of days (<= 1) spent on each project."""
    total_time = sum(event["duration"] for event in events)
    is_full_day = total_time >= employee.min_working_hours_for_full_day
    if is_full_day:
        divider = total_time
    else:
        divider = float(employee.default_day_working_hours)

    distribution: TypingCounter[str] = Counter()

    for event in events:
        distribution[event["name"]] += event["duration"] / divider  # type: ignore

    return dict(distribution)


def upcoming_weeks(events_per_employee: EventsPerEmployee, employees=List[Employee]):
    n_upcoming_weeks = 12
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())

    if employees is None:
        employees = list(events_per_employee)

    to_return: Any = {
        "weeks": [],
        "employees": list(employee.name for employee in employees),
    }
    for week_index in range(n_upcoming_weeks):
        week = start_of_current_week + datetime.timedelta(days=7 * week_index)
        end_of_week = week + datetime.timedelta(days=6)
        week_number = week.isocalendar()[1]
        to_return["weeks"].append(
            {
                "number": week_number,
                "start": f"{week.day}/{week.month}",
                "end": f"{end_of_week.day}/{end_of_week.month}",
            }
        )

    # total for each project for each employee
    projects_total: DefaultDict = defaultdict(Counter)

    for employee, employee_events in events_per_employee.items():
        to_return[employee.name] = {}
        for week_index in range(n_upcoming_weeks):
            week = start_of_current_week + datetime.timedelta(days=7 * week_index)
            end_of_week = week + datetime.timedelta(days=6)
            week_number = week.isocalendar()[1]
            projects = time_per_employee_per_month_per_project(
                {employee: employee_events}, week=week
            )["Total"]["Total"]

            for project, project_data in projects.items():
                projects_total[employee][project] += project_data["duration"]

            to_return[employee.name][week_number] = {
                "availability": available_time_of_employee(
                    employee, employee_events, week, end_of_week
                ),
                "projects": {project[0]: project[1] for project in projects},
            }
        to_return[employee.name]["projects_total"] = [
            proj[0] for proj in projects_total[employee].most_common()
        ]

    return to_return


def upcoming_months(events_per_employee: EventsPerEmployee, employees=List[Employee]):
    n_upcoming_months = 12
    today = datetime.date.today()
    start_of_current_month = today - datetime.timedelta(days=today.day - 1)

    if employees is None:
        employees = list(events_per_employee)

    to_return: Any = {
        "month_names": [],
        "employees": list(employee.name for employee in employees),
    }
    for month_index in range(n_upcoming_months):
        month = start_of_current_month + relativedelta(months=month_index)
        to_return["month_names"].append(month.strftime("%b"))

    # total for each project for each employee
    projects_total: DefaultDict = defaultdict(Counter)

    for employee, employee_events in events_per_employee.items():
        to_return[employee.name] = {}
        for month_index in range(n_upcoming_months):
            month = start_of_current_month + relativedelta(months=month_index)
            end_of_month = month + relativedelta(months=1) - relativedelta(days=1)
            month_name = month.strftime("%b")

            projects = time_per_employee_per_month_per_project(
                {employee: employee_events}, month=month
            )["Total"]["Total"]
            for project, project_data in projects.items():
                projects_total[employee][project] += project_data["duration"]
            to_return[employee.name][month_name] = {
                "availability": available_time_of_employee(
                    employee, employee_events, month, end_of_month
                ),
                "projects": {project[0]: project[1] for project in projects},
            }
        to_return[employee.name]["projects_total"] = [
            proj[0] for proj in projects_total[employee].most_common()
        ]

    return to_return


class ProjectDetail(TypedDict):
    employee: str
    date: datetime.date


class ProjectTime(TypedDict):
    duration: float
    events: List[ProjectDetail]


TimePerEmployeePerMonthPerProject = Dict[str, Dict[str, Dict[str, ProjectTime]]]


def time_per_employee_per_month_per_project(  # noqa: C901
    events_per_employee: EventsPerEmployee,
    month: datetime.date = None,
    week: datetime.date = None,
) -> TimePerEmployeePerMonthPerProject:
    """
    Counts the number of days spent per project for selected month or week.

    If week and month are None, counts the historical total.
    """
    to_return: TimePerEmployeePerMonthPerProject = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(lambda: {"duration": 0.0, "events": []})
        )
    )
    # make sure specific keys exist and are at the start
    to_return["Total"]["Total"]  # noqa
    to_return["Total"]["Total effectué"]  # noqa
    to_return["Total"]["Total à venir"]  # noqa

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

            distribution = day_distribution(events_for_day, employee=employee)

            date_keys_to_update = ["Total", month_label]
            if event_date <= datetime.date.today():
                date_keys_to_update.append("Total effectué")
            else:
                date_keys_to_update.append("Total à venir")

            for name, duration in distribution.items():
                # add both to total and relevant employee
                for employee_key in ["Total", employee.name]:
                    # add values both to total and relevant month
                    for date_key in date_keys_to_update:
                        to_return[employee_key][date_key][name]["duration"] += duration
                        to_return[employee_key][date_key][name]["events"].append(
                            {
                                "employee": employee.name,
                                "date": event_date,
                            }
                        )

    # sort by total duration for each month and total
    for employee_key, employee_values in to_return.items():
        for display_month, time_per_project in employee_values.items():
            project_names_ordered = sorted(
                time_per_project.keys(),
                key=lambda project: time_per_project[project]["duration"],
                reverse=True,
            )
            to_return[employee_key][display_month] = {
                project: to_return[employee_key][display_month][project]
                for project in project_names_ordered
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


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user
        company = request.user.employee.company
        employees = employees_for_user(user)
        today = datetime.date.today()
        display_employees = {
            employee
            for employee in employees
            if not employee.end_time_tracking_on
            or employee.end_time_tracking_on > today
        }
        project_name_finder = ProjectNameFinder()
        events_per_employee: EventsPerEmployee = get_events_for_employees(
            employees, company, project_name_finder
        )

        today = datetime.date.today()
        start_of_next_week = today + datetime.timedelta(days=7 - today.weekday())
        start_of_current_month = today.replace(day=1)
        start_of_next_month = start_of_current_month + relativedelta(months=1)
        end_of_next_month = (
            start_of_next_month + relativedelta(months=1) - relativedelta(days=1)
        )
        end_of_next_week = start_of_next_week + datetime.timedelta(days=4)

        computed_time_per_employee_per_month_per_project = (
            time_per_employee_per_month_per_project(events_per_employee)
        )
        display_employee_names = {employee.name for employee in employees}
        computed_time_per_employee_per_month_per_project = {
            employee: employee_data
            for employee, employee_data in computed_time_per_employee_per_month_per_project.items()
            if employee == "Total" or employee in display_employee_names
        }

        return {
            "active_month": list(
                computed_time_per_employee_per_month_per_project["Total"].keys()
            ).index(today.strftime("%b %y")),
            "today": datetime.date.today(),
            "events": events_per_employee,
            "employees": employees,
            "display_employees": display_employees,
            "time_per_employee_per_month_per_project_str": json.dumps(
                computed_time_per_employee_per_month_per_project,
                default=str,
            ),
            "past_week_state": state_of_days_per_employee_for_week(
                events_per_employee, today - datetime.timedelta(days=7)
            ),
            "curent_week_state": state_of_days_per_employee_for_week(
                events_per_employee, today, employees
            ),
            "next_week_availability": {
                employee: available_time_of_employee(
                    employee, events, start_of_next_week, end_of_next_week
                )
                for employee, events in events_per_employee.items()
            },
            "current_month_availability": {
                employee: available_time_of_employee(
                    employee,
                    events,
                    start_of_current_month,
                    start_of_next_month - relativedelta(days=1),
                )
                for employee, events in events_per_employee.items()
            },
            "next_month_availability": {
                employee: available_time_of_employee(
                    employee, events, start_of_next_month, end_of_next_month
                )
                for employee, events in events_per_employee.items()
            },
            "upcoming_weeks_str": json.dumps(
                upcoming_weeks(events_per_employee, display_employees)
            ),
            "upcoming_months_str": json.dumps(
                upcoming_months(events_per_employee, display_employees)
            ),
        }
