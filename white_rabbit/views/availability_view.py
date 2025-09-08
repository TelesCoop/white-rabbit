import copy
import datetime
from collections import Counter, defaultdict
from typing import Dict

from django.shortcuts import render
from django.views.generic import TemplateView

from white_rabbit.events import (
    EventsPerEmployee,
    get_events_from_employees_from_cache,
    employees_for_user,
    process_employees_events,
)
from white_rabbit.services.forecast_service import ForecastService
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.utils import generate_time_periods


class AvailabilityBaseView(TemplateView):
    template_name = "pages/availability.html"

    def __init__(self, time_period, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_period = time_period

    def retrieve_forecasted_projects(
        self, user, employees, projects_per_period, availability
    ):
        """Add forecast projects to the data structure using EmployeeForecastAssignment"""
        forecast_service = ForecastService(self.time_period)
        return forecast_service.retrieve_forecasted_projects(
            user, employees, projects_per_period, availability
        )

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

        availabitily_with_forceast = copy.deepcopy(availability)
        forecast_projects = self.retrieve_forecasted_projects(
            user, employees, projects_per_period, availabitily_with_forceast
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
                "is_forecast": True,
            }
            for fp in forecast_projects
        }
        all_projects = {**regular_projects, **forecast_projects_dict}

        context = {
            "projects_per_period": projects_per_period,
            "availability": availability,
            "availability_with_forecast": availabitily_with_forceast,
            "projects": all_projects,
            "periodicity": self.time_period,
            "periods_per_key": {
                period["key"]: period
                for period in generate_time_periods(12, self.time_period)
            },
            "is_monthly_hours": self.time_period == "month",
        }

        return render(request, self.template_name, context)


class AvailabilityPerWeekView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__("week", *args, **kwargs)


class AvailabilityPerMonthView(AvailabilityBaseView):
    def __init__(self, *args, **kwargs):
        super().__init__("month", *args, **kwargs)


class MonthlyWorkingHoursView(TemplateView):
    template_name = "pages/monthly_hours.html"

    def get_context_data(self, **kwargs):
        """
        Similar to availability.
        In this view however, we compute for each (employee, month) the total
        of hours worked in the month.
        We do not take into account time spent on project whose categories are marked as
        non-working (time off, bank holiday, OKLM, ...).
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
        worked_hours: Dict[str, Dict[str, float]] = defaultdict(Counter)
        for employee_name, employee_events in events_per_employee.items():
            projects_per_period[employee_name]  # noqa, creating key with defaultdict
            periods = employee_events.group_by_time_period(
                "month", time_shift_direction=time_direction, n_periods=n_periods
            )
            for period_key, period_data in periods.items():
                # sum duration of all events for that period
                worked_hours[employee_name][period_key] = sum(
                    event["duration"] for event in period_data["events"]
                )

        return {
            "projects_per_period": projects_per_period,
            "worked_hours": worked_hours,
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
