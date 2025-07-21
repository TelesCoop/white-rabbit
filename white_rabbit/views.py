import csv
import datetime
from collections import Counter, defaultdict
from typing import Dict

from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from .events import (
    EventsPerEmployee,
    get_events_from_employees_from_cache,
    employees_for_user,
    process_employees_events,
)
from .financial_tracking import calculate_financial_indicators
from .models import (
    Project,
    Employee,
    PROJECT_CATEGORIES_CHOICES,
    ForecastProject,
    EmployeeForecastAssignment,
)
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

    def retrieve_forecasted_projects(
        self, user, employees, projects_per_period, availability
    ):
        """Add forecast projects to the data structure using EmployeeForecastAssignment"""
        forecast_projects = ForecastProject.objects.filter(
            company=user.employee.company,
            is_forecast=True,
            start_date__isnull=False,
            end_date__isnull=False,
        )

        periods_list = list(generate_time_periods(12, self.time_period))

        # Get all forecast assignments for the company's employees
        assignments = EmployeeForecastAssignment.objects.filter(
            forecast_project__company=user.employee.company,
            forecast_project__is_forecast=True,
            forecast_project__start_date__isnull=False,
            forecast_project__end_date__isnull=False,
        ).select_related("employee__user", "forecast_project")

        for assignment in assignments:
            forecast_project = assignment.forecast_project
            employee_name = assignment.employee.name

            # Calculate which periods this assignment spans
            assignment_periods = []
            for period in periods_list:
                period_start = period["start"]
                period_end = period["end"]

                # Check if assignment overlaps with this period
                if (
                    assignment.start_date <= period_end
                    and assignment.end_date >= period_start
                ):
                    assignment_periods.append(period["key"])

            if assignment_periods:
                # Convert hours to days (assuming default working hours per day)
                daily_hours = assignment.employee.default_day_working_hours
                total_days = float(assignment.estimated_hours) / daily_hours
                # Distribute estimated days across periods
                days_per_period = total_days / len(assignment_periods)

                # Add only to the specific assigned employee
                for period_key in assignment_periods:
                    projects_per_period[employee_name][forecast_project.id][
                        period_key
                    ] += days_per_period

                    # Subtract forecasted days from employee availability
                    if (
                        employee_name in availability
                        and period_key in availability[employee_name]
                    ):
                        availability[employee_name][period_key] -= days_per_period

        return forecast_projects

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
                self.time_period, time_shift_direction="future", n_periods=12
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
        forecast_projects = self.retrieve_forecasted_projects(
            user, employees, projects_per_period, availability
        )
        # Combine regular projects with forecast projects for display
        regular_projects = project_finder.by_company(user.employee.company)
        forecast_projects_dict = {
            fp.id: {
                "name": fp.name,
                "start_date": fp.start_date and fp.start_date.strftime("%b %y"),
                "end_date": fp.end_date and fp.end_date.strftime("%b %y"),
                "category": fp.category
                or {"name": "inconnue", "color": "bg-white-100"},
            }
            for fp in forecast_projects
        }
        all_projects = {**regular_projects, **forecast_projects_dict}

        return render(
            request,
            self.template_name,
            {
                "projects_per_period": projects_per_period,
                "availability": availability,
                "projects": all_projects,
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


class MonthlyWorkingHoursView(TemplateView):
    template_name = "pages/availability.html"

    def get_context_data(self, **kwargs):
        """
        We use the same template as the availability page because the html structure is
        similar. In this view however, we compute for each (employee, month) the total
        of hours worked in the month.
        We do not take into account time spent on project whose categories are marked as
        non-working.
        """
        request = self.request
        user = request.user
        employees = employees_for_user(user)
        today = datetime.date.today()
        employees = [
            employee
            for employee in employees
            if not employee.end_time_tracking_on
            or employee.end_time_tracking_on > today
        ]
        n_periods = 12
        time_direction = "past"

        project_finder = ProjectFinder()
        events: EventsPerEmployee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )
        events_per_employee = process_employees_events(events, n_periods=n_periods)

        # index by employee, then by project, then by period
        # mostly empty for this view, but similar structure than availability view
        projects_per_period: Dict[str, Dict[int, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(Counter)
        )
        # indexed by employee then by period
        availability: Dict[str, Dict[str, float]] = defaultdict(Counter)
        for employee_name, employee_events in events_per_employee.items():
            projects_per_period[employee_name]  # noqa, creating key with defaultdict
            periods = employee_events.group_by_time_period(
                "month", time_shift_direction=time_direction, n_periods=n_periods
            )
            for period_key, period_data in periods.items():
                # sum duration of all events for that period
                availability[employee_name][period_key] = sum(
                    event["duration"] for event in period_data["events"]
                )

        return {
            "projects_per_period": projects_per_period,
            "availability": availability,
            "projects": project_finder.by_company(user.employee.company),
            "periodicity": "month",
            "periods_per_key": {
                period["key"]: period
                for period in generate_time_periods(
                    n_periods, "month", time_shift_direction=time_direction
                )
            },
            "is_monthly_hours": True,
        }


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


class AbstractTotalView(TemplateView):
    template_name = "pages/projects-or-categories-total.html"

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "html")
        if format_type == "csv":
            return self.export_csv(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def export_csv(self, request, *args, **kwargs):
        """Export the data as a CSV file."""
        context = self.get_context_data(**kwargs)

        show_details = context.get("show_details", False)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{kwargs.get("period", "data")}{"-details" if show_details else ""}.csv"'
        )

        writer = csv.writer(response)

        # Write header row
        header = self._get_csv_header(context)
        writer.writerow(header)

        # Write data rows for each project/category
        for identifier in context["identifier_order"]:
            # Write the main project/category row
            self._write_project_row(writer, context, identifier)

            # Write subproject/subcategory rows if details are requested
            if show_details and identifier in context["subtotal_per_identifier"]:
                self._write_subproject_rows(writer, context, identifier)

        return response

    def _get_csv_header(self, context):
        """Generate the CSV header row."""
        group_by = context.get("group_by", "project")
        header = [group_by.capitalize(), "Total"]

        # Add employee names to header
        employees_names = context.get("employees_names", [])
        for employee_name in employees_names:
            header.append(employee_name)

        return header

    def _get_project_name(self, context, identifier):
        """Get the name of a project or category."""
        group_by = context.get("group_by", "project")
        name = ""

        if group_by == "project" and identifier in context["details_data"]:
            name = context["details_data"][identifier]["name"]
        elif group_by == "category":
            for category_id, category_name in context["details_data"]:
                if category_id == identifier:
                    name = category_name
                    break

        return name or str(identifier)

    def _write_project_row(self, writer, context, identifier):
        """Write a row for a project or category."""
        total = context["total_per_identifier"][identifier]
        name = self._get_project_name(context, identifier)

        # Create row with project/category name and total
        row = [name, f"{total:.1f}"]

        # Add data for each employee
        employees_names = context.get("employees_names", [])
        for employee_name in employees_names:
            employee_events = context["employees_events"].get(employee_name, {})
            project_data = employee_events.get(identifier, {})
            duration = project_data.get("duration", 0)
            row.append(f"{duration:.1f}" if duration else "")

        writer.writerow(row)

    def _write_subproject_rows(self, writer, context, identifier):
        """Write rows for subprojects or subcategories."""
        employees_names = context.get("employees_names", [])

        for sub_name, sub_total in context["subtotal_per_identifier"][
            identifier
        ].items():
            # Create row with subproject/subcategory name and total
            sub_row = [f"  {sub_name}", f"{sub_total:.1f}"]

            # Add data for each employee
            for employee_name in employees_names:
                employee_events = context["employees_events"].get(employee_name, {})
                project_data = employee_events.get(identifier, {})
                subprojects = project_data.get("subprojects", {})
                sub_data = subprojects.get(sub_name, {})
                sub_duration = sub_data.get("duration", 0)
                sub_row.append(f"{sub_duration:.1f}" if sub_duration else "")

            writer.writerow(sub_row)

    def get_context_data(self, group_by, **kwargs):
        assert group_by in ["category", "project"]
        request = self.request
        user = request.user
        details = bool(self.request.GET.get("details", False))

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
                    subtotal_per_identifier[project_id][
                        sub_project_name or "Non attribué"
                    ] += data["duration"]
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

        project_details_data = project_finder.by_company(user.employee.company)
        if group_by == "category":
            details_data = PROJECT_CATEGORIES_CHOICES
        else:
            details_data = project_details_data
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
            "project_details_data": project_details_data,
            "group_by": group_by,
            "show_details": details,
            "company": user.employee.company,
            "url_key": "projects" if group_by == "project" else "categories",
        }


class TotalPerProjectView(AbstractTotalView):
    def get_context_data(self, **kwargs):
        return super().get_context_data(group_by="project", **kwargs)


class DistributionView(AbstractTotalView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(group_by="category", **kwargs)

        # Check if proportional display is requested
        proportional = bool(self.request.GET.get("proportional", False))
        context["show_proportional"] = proportional

        if proportional:
            # Compute proportional values for the total column
            total_per_identifier = context["total_per_identifier"]
            grand_total = sum(total_per_identifier.values())

            proportional_totals = {}
            for identifier, total in total_per_identifier.items():
                if grand_total > 0:
                    proportion = (total / grand_total) * 100
                    proportional_totals[identifier] = proportion
                else:
                    proportional_totals[identifier] = 0

            context["proportional_totals"] = proportional_totals

            # Compute proportional values for each employee column
            employees_events = context["employees_events"]
            proportional_data = {}

            for employee_name, employee_data in employees_events.items():
                # Compute total for this employee across all categories
                employee_total = sum(
                    project_time["duration"] for project_time in employee_data.values()
                )

                # Compute proportional values for each category
                proportional_data[employee_name] = {}
                for category_id, project_time in employee_data.items():
                    if employee_total > 0:
                        proportion = (project_time["duration"] / employee_total) * 100
                        proportional_data[employee_name][category_id] = proportion
                    else:
                        proportional_data[employee_name][category_id] = 0

            context["proportional_data"] = proportional_data

        return context


class EstimatedDaysCountView(AbstractTotalView):
    template_name = "pages/estimated-days-count.html"

    def get_context_data(self, is_full=False, **kwargs):
        context = super().get_context_data(
            group_by="project", period="total_done", **kwargs
        )
        projects = Project.objects.filter(company=self.request.user.employee.company)
        if not is_full:
            today = datetime.date.today()
            two_months_ago = today - datetime.timedelta(days=60)
            projects = projects.filter(
                Q(start_date__lte=today) | Q(start_date__isnull=True)
            ).filter(Q(end_date__gte=two_months_ago) | Q(end_date__isnull=True))
        projects_by_id = {project.pk: project for project in projects}

        projects_data: Dict[str, Dict[str, int]] = {
            project.id: {
                "estimated_days_count": (estimated := project.estimated_days_count),
                "done": (done := context["total_per_identifier"][project_id]),
                "remaining": float(estimated) - done,
                "id": project_id,
                "name": project.name,
                "start_date": (
                    project.start_date.strftime("%m/%y") if project.start_date else ""
                ),
                "end_date": (
                    project.end_date.strftime("%m/%y") if project.end_date else ""
                ),
            }
            for project_id in context["identifier_order"]
            if project_id in projects_by_id
            and (project := projects_by_id[project_id]).estimated_days_count
        }
        context["projects_data"] = projects_data
        context["is_full"] = is_full
        return context


class FinancialTrackingView(AbstractTotalView):
    template_name = "pages/financial-tracking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            group_by="project", period="total_done", **kwargs
        )
        company = self.request.user.employee.company

        context["daily_employee_cost"] = int(company.daily_employee_cost)
        context["profitability_threshold"] = int(company.profitability_threshold)
        context["daily_market_price"] = int(company.daily_market_price)

        financial_indicators = calculate_financial_indicators(
            company, context["identifier_order"], context["total_per_identifier"]
        )

        context = {**context, **financial_indicators}

        return context
