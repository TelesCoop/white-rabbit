import datetime
import json
from functools import lru_cache
from typing import (
    List,

)
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.views.generic import TemplateView

from .events import (
    EventsPerEmployee,
    get_events_for_employees,
    employees_for_user
)
from .models import  Project, Company
from .project_name_finder import ProjectNameFinder
from .state_of_day import (
    state_of_days_per_employee_for_week,
)
from .upcoming import UpcomingEvents


class MyLoginView(LoginView):
    template_name = "admin/login.html"


def client_projects_for_company(company: Company) -> List[Project]:
    return list(Project.objects.filter(is_client_project=True, company=company))


def pro_bono_projects_for_company(company: Company) -> List[Project]:
    return list(Project.objects.filter(is_pro_bono_project=True, company=company))


def add_done_and_remaining_days_to_projects(project_list_by_type, employee_monthly_details):
    for project_list in project_list_by_type:
        for project in project_list:
            try:
                project.done = employee_monthly_details["Total"][
                    "Total effectué"
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
        project_name_finder = ProjectNameFinder()
        events_per_employee: EventsPerEmployee = get_events_for_employees(
            employees, project_name_finder, request=self.request
        )
        return {
            "past_week_state": json.dumps(state_of_days_per_employee_for_week(
                events_per_employee, today - datetime.timedelta(days=7)
            ), default=str),
             "curent_week_state": json.dumps(state_of_days_per_employee_for_week(
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

        project_name_finder = ProjectNameFinder()
        events_per_employee: EventsPerEmployee = get_events_for_employees(
            employees, project_name_finder, request=self.request
        )
        upcoming_events = UpcomingEvents(events_per_employee, self.time_period)
        up_events = upcoming_events.events()
        up_periods = upcoming_events.periods()
        project_details = project_name_finder.projects_for_company(
            user.employee.company
        )
        return render(request, self.template_name, {
            "employees": json.dumps([employee.name for employee in display_employees]),
            "events": json.dumps(up_events, default=str),
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


class TotalPerProjectView(TemplateView):
    template_name = "components/total-per-project.html"

    def get_context_data(self, **kwargs):
        # request = self.request
        # user = request.user
        # employees = employees_for_user(user)
        # project_name_finder = ProjectNameFinder()
        # events_per_employee: EventsPerEmployee = get_events_for_employees(
        #     employees, project_name_finder, request=self.request
        # )
        #
        # employee_monthly_details = (
        #     month_detail_per_employee_per_month(events_per_employee)
        # )
        # display_employee_names = {employee.name for employee in employees}
        # # filter out employees we are not supposed to know about
        # employee_monthly_details = {
        #     employee: employee_data
        #     for employee, employee_data in employee_monthly_details.items()
        #     if employee == "Total" or employee in display_employee_names
        # }

        return {
            # "month_detail_per_employee": json.dumps(
            #     employee_monthly_details,
            #     default=str,
            # ),
            "test": {
                "project": 1
            },
            "test_2": ["project"]
        }
