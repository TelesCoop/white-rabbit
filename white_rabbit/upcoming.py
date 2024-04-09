from collections import defaultdict, Counter
import datetime
from typing import List, Any, DefaultDict

from dateutil.relativedelta import relativedelta

from white_rabbit.available_time import available_time_of_employee
from white_rabbit.events import month_detail_per_employee_per_month
from white_rabbit.models import Employee
from white_rabbit.typing import EventsPerEmployee


class UpcomingEvents:
    def __init__(self, events_per_employee: EventsPerEmployee, time_period: str):
        if time_period not in ["week", "month"]:
            raise NotImplementedError("time_period must be one of week, month")

        self.time_period = time_period
        self.n_upcoming_periods = 12
        self.today = datetime.date.today()
        self.days_delta = self.today.day - 1 if self.is_month_period else self.today.weekday()
        self.start_of_current_period = self.today - datetime.timedelta(days=self.days_delta)
        self.events_per_employee = events_per_employee
    @property
    def is_month_period(self):
        return self.time_period == "month"

    def get_period_start(self, period_index):
        return self.start_of_current_period + relativedelta(
            **{f"{self.time_period}s": period_index}
        )

    def periods(self):
        periods: Any = []
        for period_index in range(self.n_upcoming_periods):
            period_start = self.get_period_start(period_index)
            if self.is_month_period:
                period_key = f"{period_start.strftime("%b")} {period_start.year}"
                end_of_period  = None
                start_of_period = None
            else:
                period_key = f"Semaine n°{period_start.isocalendar()[1]}"
                end_of_period = period_start + datetime.timedelta(days=6)
                start_of_period = f"{period_start.day}/{period_start.month}"

            periods.append({"key": period_key, "start": start_of_period, "end": end_of_period})

        return periods

    def calculate_period_key(self, period_start):
        if self.is_month_period:
            return period_start.strftime("%b")
        else:
            return period_start.isocalendar()[1]

    def calculate_projects(self, employee, employee_events, period_start):
        return month_detail_per_employee_per_month(
            {employee: employee_events}, **{self.time_period: period_start}
        )["Total"]["Total"]["values"]

    def calculate_total_projects(self, employee, projects_total):
        return [proj[0] for proj in projects_total[employee].most_common()]

    def events(self):
        events: Any = {}
        projects_total: DefaultDict = defaultdict(Counter)

        for employee, employee_events in self.events_per_employee.items():
            events[employee.name] = {}

            for period_index in range(self.n_upcoming_periods):
                period_start = self.get_period_start(period_index)
                period_end = (
                        period_start
                        + relativedelta(**{f"{self.time_period}s": 1})  # type: ignore
                        - relativedelta(days=1)
                )

                period_key = self.calculate_period_key(period_start)
                projects = self.calculate_projects(employee, employee_events, period_start)

                for project_id, project_data in projects.items():
                    projects_total[employee][project_id] += project_data["duration"]

                events[employee.name][period_key] = {
                    "availability": available_time_of_employee(
                        employee, employee_events, period_start, period_end
                    ),
                    "projects": projects,
                }

            events[employee.name]["projects_total"] = self.calculate_total_projects(employee, projects_total)

        return events

