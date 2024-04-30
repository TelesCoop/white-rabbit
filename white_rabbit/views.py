import datetime
import json
from functools import lru_cache
from typing import (
    List,

)

import jsonpickle
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.views.generic import TemplateView

from .events import (
    EventsPerEmployee,
    get_events_from_employees_from_cache,
    employees_for_user, process_employees_events, EmployeeEvents
)
from .models import Project, Company, Employee
from .project_name_finder import ProjectFinder
from .state_of_day import (
    state_of_days_per_employee_for_week,
)
from .upcoming import UpcomingEvents
from .utils import generate_time_periods, get_or_create_project, get_or_create_employee_event, \
    get_or_create_project_by_employee_and_category


class MyLoginView(LoginView):
    template_name = "admin/login.html"


def add_done_and_remaining_days_to_projects(project_list_by_type, employee_monthly_details):
    for project_list in project_list_by_type:
        for project in project_list:
            try:
                project.done = employee_monthly_details["total"][
                    "completed"
                ]["values"][project.pk]["duration"]
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
            "past_week_events": json.dumps(state_of_days_per_employee_for_week(
                events_per_employee, today - datetime.timedelta(days=7)
            ), default=str),
            "current_week_event": json.dumps(state_of_days_per_employee_for_week(
                events_per_employee, today, employees
            ), default=str),
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

        upcoming_events = [employee_events.upcoming_events(self.time_period) for employee_name, employee_events in
                           events_per_employee.items()]
        up_periods = generate_time_periods(12, self.time_period)

        project_details = project_finder.by_company(
            user.employee.company
        )

        return render(request, self.template_name, {
            "employees": json.dumps([employee.name for employee in display_employees]),
            "events": upcoming_events,
            "periods": json.dumps(up_periods, default=str),
            "projects": project_details,
            "title": self.title,
            "periodicity": self.time_period,
        })


class AvailabilityPerWeekView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__("week", "Disponibilités pour les prochaines semaines", *args, **kwargs)


class AvailabilityPerMonthView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__("month", "Disponibilités pour les prochains mois", *args, **kwargs)


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
        up_events = EmployeeEvents(employee, events[employee], 1).upcoming_events("week")
        project_details = project_finder.by_company(
            employee.company
        )
        return {
            "events": up_events,
            "projects_details": project_details
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

        employees_events = (
            process_employees_events(events_per_employee, 24)
        )

        projects = {}
        total_days = {}

        for employee_name, employee_events in employees_events.items():
            total_per_projects = employee_events.total_per_projects()

            for month, project_details in total_per_projects.items():
                for project_id, project_detail in project_details["projects"].items():

                    if month not in projects:
                        projects[month] = {}

                    project = get_or_create_project(projects[month], project_id, project_detail)
                    project["employees_events"][employee_name] = get_or_create_employee_event(
                        project["employees_events"],
                        employee_name, project_detail)

                    total_day = get_or_create_project(total_days, project_id, project_detail)
                    total_day["employees_events"][employee_name] = get_or_create_employee_event(
                        total_day["employees_events"],
                        employee_name, project_detail)

        projects_per_month = {**{"Total": total_days}, **projects}

        return {
            "employees_events": employees_events,
            "employees_names": employees_names,
            "projects_per_month": projects_per_month,
            "projects_details": project_finder.by_company(
                user.employee.company
            ),
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
        employees_events = (
            process_employees_events(events_per_employee, 1)
        )
        projects = {}
        categories = set()
        for employee_name, employee_events in employees_events.items():
            total_per_employee_and_project = employee_events.total_per_employee_and_project_category()

            for month, project_employee_events_by_category in total_per_employee_and_project.items():
                for employee, projects_events_by_category in project_employee_events_by_category.items():
                    for project_category, projects_events_by_category in projects_events_by_category.items():
                        projects = get_or_create_project_by_employee_and_category(
                            projects,
                            project_category,
                            employee,
                            projects_events_by_category
                        )
                        categories.add(project_category)
        return {
            "employees_names": employees_names,
            "projects": projects,
            "categories": categories
        }
