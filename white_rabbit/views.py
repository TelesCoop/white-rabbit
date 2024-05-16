import datetime
import json
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.views.generic import TemplateView

from .events import (
    EventsPerEmployee,
    get_events_from_employees_from_cache,
    employees_for_user,
    process_employees_events,
)
from .models import Project, Employee, PROJECT_CATEGORIES_CHOICES
from .project_name_finder import ProjectFinder
from .state_of_day import (
    state_of_days_per_employee_for_week,
)
from .utils import generate_time_periods, generate_time_periods_with_total


class MyLoginView(LoginView):
    template_name = "admin/login.html"


def add_done_and_remaining_days_to_projects(
    project_list_by_type, employee_monthly_details
):
    for project_list in project_list_by_type:
        for project in project_list:
            try:
                project.done = employee_monthly_details["total"]["completed"]["values"][
                    project.pk
                ]["duration"]
            except KeyError:
                project.done = 0
            if project.days_sold > 0:
                project.remaining = float(project.days_sold) - project.done


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user
        employees = employees_for_user(user)
        today = datetime.date.today()
        project_finder = ProjectFinder()
        events_per_employee: EventsPerEmployee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )
        return {
            "past_week_events": json.dumps(
                state_of_days_per_employee_for_week(
                    events_per_employee, today - datetime.timedelta(days=7)
                ),
                default=str,
            ),
            "current_week_event": json.dumps(
                state_of_days_per_employee_for_week(
                    events_per_employee, today, employees
                ),
                default=str,
            ),
        }


class AvailabilityBaseView(TemplateView):
    template_name = "pages/availability.html"

    def __init__(self, time_period, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_period = time_period
        self.title = title

    def get(self, request):
        user = request.user
        employees = employees_for_user(user)
        today = datetime.date.today()
        display_employees = [
            employee
            for employee in employees
            if not employee.end_time_tracking_on
            or employee.end_time_tracking_on > today
        ]

        project_finder = ProjectFinder()
        events: EventsPerEmployee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )
        events_per_employee = process_employees_events(events, n_periods=12)

        upcoming_events = [
            {
                employee_name: employee_events.group_by_time_period(
                    self.time_period, timeshift_direction="future"
                )
            }
            for employee_name, employee_events in events_per_employee.items()
        ]
        up_periods = generate_time_periods(12, self.time_period)

        project_details = project_finder.by_company(user.employee.company)

        return render(
            request,
            self.template_name,
            {
                "employees": json.dumps(
                    [employee.name for employee in display_employees]
                ),
                "upcoming_events_by_employee_and_timeperiod": upcoming_events,
                "periods": json.dumps(up_periods, default=str),
                "projects": project_details,
                "title": self.title,
                "periodicity": self.time_period,
            },
        )


class AvailabilityPerWeekView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__(
            "week", "Disponibilités pour les prochaines semaines", *args, **kwargs
        )


class AvailabilityPerMonthView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__(
            "month", "Disponibilités pour les prochains mois", *args, **kwargs
        )


class AliasView(TemplateView):
    template_name = "pages/alias.html"

    def get_context_data(self, **kwargs):
        company = self.request.user.employee.company
        aliasesByProject = {}

        for project in Project.objects.filter(company=company).order_by("name"):
            aliasesByProject[project.name] = [
                alias.name for alias in project.aliases.all()
            ]
        return {"aliasesByProject": aliasesByProject}


class ResumeView(TemplateView):
    template_name = "pages/resume.html"

    def get_context_data(self, **kwargs):
        project_finder = ProjectFinder()
        employee = Employee.objects.get(user=self.request.user)
        events: EventsPerEmployee = get_events_from_employees_from_cache(
            [employee], project_finder, request=self.request
        )

        raw_employees_events = process_employees_events(events, 2)
        employees_events = {}

        for employee_name, employee_events in raw_employees_events.items():
            employees_events[employee_name] = {}
            employees_events[employee_name] = employee_events.group_events_per_day()

        project_details = project_finder.by_company(employee.company)
        return {
            "employees_events": employees_events,
            "current_user": self.request.user,
            "projects_details": project_details,
        }


class TotalPerProjectView(TemplateView):
    template_name = "pages/projects-total.html"

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user
        employees = employees_for_user(user)
        employees_names = {employee.name for employee in employees}
        project_finder = ProjectFinder()
        events_per_employee: EventsPerEmployee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )

        raw_employees_events = process_employees_events(events_per_employee, 24)
        employees_events = {}
        projects = {
            "total": {},
            "total_done": {},
            "total_remaining": {},
        }

        for employee_name, employee_events in raw_employees_events.items():
            employees_events[
                employee_name
            ] = employee_events.total_project_per_time_period()

        for employee_name, employee_events_per_month in employees_events.items():
            for (
                month,
                employee_events_per_projects_ids,
            ) in employee_events_per_month.items():
                if month not in projects:
                    projects[month] = {}

                for project_id, events in employee_events_per_projects_ids.items():
                    if project_id not in projects[month]:
                        projects[month][project_id] = {
                            "duration": 0,
                            "days": 0,
                            "events": {},
                        }

                    projects[month][project_id]["duration"] += events["duration"]
                    projects[month][project_id]["days"] += events["days_spent"]
                    projects[month][project_id]["project_id"] = project_id
                    if employee_name not in projects[month][project_id]["events"]:
                        projects[month][project_id]["events"][employee_name] = []
                    projects[month][project_id]["events"][employee_name] = events

                    if project_id not in projects["total"]:
                        projects["total"][project_id] = {
                            "duration": 0,
                            "days": 0,
                            "events": {},
                        }

                    projects["total"][project_id]["duration"] += events["duration"]
                    projects["total"][project_id]["days"] += events["days_spent"]
                    projects["total"][project_id]["project_id"] = project_id
                    if employee_name not in projects["total"][project_id]["events"]:
                        projects["total"][project_id]["events"][employee_name] = {
                            "duration": 0,
                            "days_spent": 0,
                            "events": [],
                        }
                    projects["total"][project_id]["events"][employee_name][
                        "duration"
                    ] += events["duration"]
                    projects["total"][project_id]["events"][employee_name][
                        "days_spent"
                    ] += events["days_spent"]

                    projects["total"][project_id]["events"][employee_name][
                        "events"
                    ].extend(events["events"])

        sorted_projects = {}
        for month, projects_in_month in projects.items():
            sorted_projects_in_month = dict(
                sorted(
                    projects_in_month.items(),
                    key=lambda item: item[1]["duration"],
                    reverse=True,
                )
            )
            sorted_projects[month] = sorted_projects_in_month

        return {
            "employees_events": employees_events,
            "employees_names": employees_names,
            "periods": generate_time_periods_with_total(
                24, time_shift_direction="past"
            ),
            "employees_events_per_month": sorted_projects,
            "projects_details": project_finder.by_company(user.employee.company),
        }


class DistributionView(TemplateView):
    template_name = "pages/distribution.html"

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user
        employees = employees_for_user(user)
        employees_names = {employee.name for employee in employees}

        # For each employee, count the number of days they have worked on each category of project per month

        project_finder = ProjectFinder()
        events_per_employee: EventsPerEmployee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )
        employees_events = process_employees_events(events_per_employee, 12)
        projects = {}
        for employee_name, employee_events in employees_events.items():
            if employee_name not in projects:
                projects[employee_name] = {}
            projects[
                employee_name
            ] = employee_events.total_per_time_period_and_project_category()

        return {
            "employees_names": employees_names,
            "projects": projects,
            "categories": PROJECT_CATEGORIES_CHOICES,
            "periods": generate_time_periods(24, time_shift_direction="past"),
        }
