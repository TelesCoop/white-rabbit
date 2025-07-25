from collections import Counter, defaultdict

from ..models import ForecastProject, EmployeeForecastAssignment
from ..utils import generate_time_periods


class ForecastService:
    """Service for handling forecast project operations"""

    def __init__(self, time_period: str):
        self.time_period = time_period

    def get_forecast_projects_for_company(self, company):
        """Get all forecast projects for a company with required dates"""
        return ForecastProject.objects.filter(
            company=company,
            is_forecast=True,
            start_date__isnull=False,
            end_date__isnull=False,
        )

    def get_assignments_for_company(self, company):
        """Get all forecast assignments for a company's employees"""
        return EmployeeForecastAssignment.objects.filter(
            forecast_project__company=company,
            forecast_project__is_forecast=True,
            forecast_project__start_date__isnull=False,
            forecast_project__end_date__isnull=False,
        ).select_related("employee__user", "forecast_project")

    def get_assignment_dates(self, assignment):
        """Get the effective start and end dates for an assignment"""
        assignment_start = (
            assignment.start_date or assignment.forecast_project.start_date
        )
        assignment_end = assignment.end_date or assignment.forecast_project.end_date
        return assignment_start, assignment_end

    def calculate_overlapping_periods(
        self, assignment_start, assignment_end, periods_list
    ):
        """Calculate which periods an assignment overlaps with"""
        assignment_periods = []
        for period in periods_list:
            period_start = period["start"]
            period_end = period["end"]

            # Check if assignment overlaps with this period
            if assignment_start <= period_end and assignment_end >= period_start:
                assignment_periods.append(period["key"])

        return assignment_periods

    def distribute_assignment_days(self, assignment, assignment_periods):
        """Distribute estimated days across periods for an assignment"""
        if not assignment_periods:
            return {}

        total_days = float(assignment.estimated_days)
        days_per_period = total_days / len(assignment_periods)

        return {period_key: days_per_period for period_key in assignment_periods}

    def update_employee_data(
        self,
        employee_name,
        forecast_project,
        period_distribution,
        projects_per_period,
        availability,
    ):
        """Update projects_per_period and availability for an employee"""
        # Ensure the employee exists in data structures
        if employee_name not in projects_per_period:
            projects_per_period[employee_name] = defaultdict(Counter)

        if employee_name not in availability:
            availability[employee_name] = Counter()

        # Add project data
        projects_per_period[employee_name][forecast_project.id] = period_distribution

        # Update availability
        for period_key, days in period_distribution.items():
            if period_key in availability[employee_name]:
                availability[employee_name][period_key] -= days

    def retrieve_forecasted_projects(
        self, user, employees, projects_per_period, availability
    ):
        """Add forecast projects to the data structure using EmployeeForecastAssignment"""
        periods_list = list(generate_time_periods(12, self.time_period))
        assignments = self.get_assignments_for_company(user.employee.company)

        for assignment in assignments:
            forecast_project = assignment.forecast_project
            employee_name = assignment.employee.name

            # Get effective assignment dates
            assignment_start, assignment_end = self.get_assignment_dates(assignment)

            # Skip if we still don't have dates
            if not assignment_start or not assignment_end:
                continue

            # Calculate overlapping periods
            assignment_periods = self.calculate_overlapping_periods(
                assignment_start, assignment_end, periods_list
            )

            if assignment_periods:
                # Distribute days across periods
                period_distribution = self.distribute_assignment_days(
                    assignment, assignment_periods
                )

                # Update employee data
                self.update_employee_data(
                    employee_name,
                    forecast_project,
                    period_distribution,
                    projects_per_period,
                    availability,
                )

        return self.get_forecast_projects_for_company(user.employee.company)
