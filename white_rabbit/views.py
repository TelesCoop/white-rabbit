import datetime
from collections import Counter, defaultdict
from typing import Dict

from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.views.generic import TemplateView

from .events import (
    EventsPerEmployee,
    get_events_from_employees_from_cache,
    employees_for_user,
    process_employees_events,
)
from .models import Project, Employee, PROJECT_CATEGORIES_CHOICES, ProjectCategories
from .project_name_finder import ProjectFinder
from .state_of_day import (
    state_of_days_per_employee_for_week,
)
from .typing import ProjectTime
from .utils import (
    generate_time_periods,
    generate_time_periods_with_total,
    time_period_for_month,
    is_total_key,
    is_year_key,
)


class MyLoginView(LoginView):
    template_name = "admin/login.html"


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
            "employees": employees,
            "past_week_events": state_of_days_per_employee_for_week(
                events_per_employee, today - datetime.timedelta(days=7)
            ),
            "current_week_event": state_of_days_per_employee_for_week(
                events_per_employee, today, employees
            ),
        }


class AvailabilityBaseView(TemplateView):
    template_name = "pages/availability.html"

    def __init__(self, time_period, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_period = time_period

    def get(self, request):
        user = request.user
        employees = employees_for_user(user)
        today = datetime.date.today()
        employees = [
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

        # index by employee, then by project, then by period
        projects_per_period: Dict[str, Dict[int, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(Counter)
        )
        # indexed by employee then by period
        availability: Dict[str, Dict[str, float]] = defaultdict(Counter)
        for employee_name, employee_events in events_per_employee.items():
            periods = employee_events.group_by_time_period(
                self.time_period, timeshift_direction="future", n_periods=12
            )
            for period_key, period_data in periods.items():
                availability[employee_name][period_key] = period_data["availability"]
                data = employee_events.projects_for_time_period(
                    period_data["period"], self.time_period, group_by="project"
                )
                for project_id, project_data in data.items():
                    projects_per_period[employee_name][project_id][
                        period_key
                    ] += project_data["duration"]

        # for each employee, re-order projects by total upcoming time
        for employee in projects_per_period.keys():
            projects_per_period[employee] = dict(
                sorted(
                    projects_per_period[employee].items(),
                    key=lambda item: sum(item[1].values()),
                    reverse=True,
                )
            )

        return render(
            request,
            self.template_name,
            {
                "projects_per_period": projects_per_period,
                "availability": availability,
                "projects": project_finder.by_company(user.employee.company),
                "periodicity": self.time_period,
                "periods_per_key": {
                    period["key"]: period
                    for period in generate_time_periods(12, self.time_period)
                },
            },
        )


class AvailabilityPerWeekView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__("week", *args, **kwargs)


class AvailabilityPerMonthView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__("month", *args, **kwargs)


class AliasView(TemplateView):
    template_name = "pages/alias.html"

    def get_context_data(self, **kwargs):
        company = self.request.user.employee.company
        aliasesByProject = {}

        for project in Project.objects.filter(company=company).order_by("name"):
            if project.aliases.count():
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


class AbstractTotalView(TemplateView):
    template_name = "pages/projects-or-categories-total.html"

    def get_context_data(self, group_by, **kwargs):
        assert group_by in ["category", "project"]
        request = self.request
        user = request.user
        details = self.request.GET.get("details", False)

        # period is a month, a year, or one of total, total_done, total_todo
        period_name = kwargs["period"]
        if is_total_key(period_name):
            if is_year_key(period_name):
                year = int(period_name.split("-")[1])
                start = datetime.date(year, 1, 1)
                end = datetime.date(year + 1, 1, 1)
                time_period_type = "year"
            else:
                start = datetime.date(2020, 1, 1)
                end = datetime.date(2030, 1, 1)
                time_period_type = None
            period = {
                "key": period_name,
                "start": start,
                "end": end,
            }
        else:
            time_period_type = "month"
            period = time_period_for_month(period_name)

        employees = employees_for_user(user)
        employees_names = {employee.name for employee in employees}
        project_finder = ProjectFinder()

        events_per_employee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )
        events_per_employee = process_employees_events(events_per_employee, 24)

        employees_events: Dict[str, Dict[int, ProjectTime]] = {}
        for employee_name, employee_events in events_per_employee.items():
            employees_events[employee_name] = employee_events.projects_for_time_period(
                period, time_period_type, group_by=group_by
            )

        total_per_identifier = Counter()
        subtotal_per_identifier: Dict[int, Dict[str, float]] = defaultdict(Counter)
        for _, employee_events in employees_events.items():
            for project_id, project_time in employee_events.items():
                total_per_identifier[project_id] += project_time["duration"]
                for sub_project_name, data in project_time["subprojects"].items():
                    subtotal_per_identifier[project_id][sub_project_name] += data[
                        "duration"
                    ]
        identifier_order = sorted(
            total_per_identifier.keys(),
            key=lambda project_id: total_per_identifier[project_id],
            reverse=True,
        )

        if details:
            # re-order subtotal_per_identifier
            for project_id in subtotal_per_identifier.keys():
                subtotal_per_identifier[project_id] = dict(
                    sorted(
                        subtotal_per_identifier[project_id].items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                )

        if group_by == "category":
            details_data = PROJECT_CATEGORIES_CHOICES
        else:
            details_data = project_finder.by_company(user.employee.company)
        return {
            "employees_events": employees_events,
            "employees_names": employees_names,
            "periods": generate_time_periods_with_total(
                24, time_shift_direction="past"
            ),
            "current_period_key": period["key"],
            "identifier_order": identifier_order,
            "total_per_identifier": total_per_identifier,
            "subtotal_per_identifier": subtotal_per_identifier,
            "details_data": details_data,
            "group_by": group_by,
            "show_details": details,
        }


class TotalPerProjectView(AbstractTotalView):
    template_name = "pages/projects-or-categories-total.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(group_by="project", **kwargs)


class DistributionView(AbstractTotalView):
    def get_context_data(self, **kwargs):
        return super().get_context_data(group_by="category", **kwargs)


class EstimatedDaysCountView(AbstractTotalView):
    template_name = "pages/estimated-days-count.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            group_by="project", period="total_done", **kwargs
        )
        projects_by_id = {
            project.pk: project
            for project in Project.objects.filter(
                company=self.request.user.employee.company
            )
        }
        projects_data: Dict[str, Dict[str, int]] = {
            project.name: {
                "estimated_days_count": (estimated := project.estimated_days_count),
                "done": (done := context["total_per_identifier"][project_id]),
                "remaining": float(estimated) - done,
                "id": project_id,
            }
            for project_id in context["identifier_order"]
            if (
                project := projects_by_id[project_id]
            ).estimated_days_count
        }
        context["projects_data"] = projects_data
        return context


class MoneyTrackingView(AbstractTotalView):
    template_name = "pages/money-tracking.html"

    def add_to_total(self, total, project):
        total["total_sold"] += project["total_sold"]
        total["real_cost"] += project["real_cost"]
        total["break_even_point"] += project["break_even_point"]
        total["opportunity_cost"] += project["opportunity_cost"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            group_by="project", period="total_done", **kwargs
        )

        projects_by_id = {
            project.pk: project
            for project in Project.objects.filter(
                company=self.request.user.employee.company
            )
        }

        projects_data: Dict[str, Dict[str, int]] = {}
        total_below_real_cost: Dict[str, int] = {
            "total_sold": 0,
            "real_cost": 0,
            "break_even_point": 0,
            "opportunity_cost": 0,
        }
        total_below_break_even_point = total_below_real_cost.copy()

        for project_id in context["identifier_order"]:
            project = projects_by_id[project_id]
            if project.end_date and project.category == ProjectCategories.CLIENT.value:
                project_name = f"{project.name} ({project.end_date.strftime('%m-%y')})"
                projects_data[project_name] = {
                    "total_sold": project.total_sold,
                    "estimated_days_count": project.estimated_days_count,
                    "done": (done := context["total_per_identifier"][project_id]),
                    "real_cost": done * float(project.company.employee_real_cost),
                    "break_even_point": done * float(project.company.break_even_point),
                    "opportunity_cost": done * float(project.company.market_cost),
                    "id": project_id,
                }
                if projects_data[project_name]["total_sold"] < projects_data[project_name]["real_cost"]:
                    self.add_to_total(total_below_real_cost, projects_data[project_name])
                elif projects_data[project_name]["total_sold"] < projects_data[project_name]["break_even_point"]:
                    self.add_to_total(total_below_break_even_point, projects_data[project_name])

        context["projects_data"] = projects_data
        context["employee_real_cost"] = int(project.company.employee_real_cost)
        context["break_even_point"] = int(project.company.break_even_point)
        context["market_cost"] = int(project.company.market_cost)
        context["total_below_real_cost"] = total_below_real_cost
        context["total_below_break_even_point"] = total_below_break_even_point
        
        return context
