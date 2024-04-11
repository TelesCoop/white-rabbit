from collections import defaultdict, Counter
import datetime
from typing import List, Any, DefaultDict

from dateutil.relativedelta import relativedelta

from white_rabbit.available_time import available_time_of_employee
from white_rabbit.events import process_employees_events
from white_rabbit.typing import EventsPerEmployee


class UpcomingEvents:
    def __init__(self, events_per_employee: EventsPerEmployee, time_period: str, n_upcoming_periods: int = 12):
        if time_period not in ["week", "month"]:
            raise NotImplementedError("time_period must be one of week, month")

        self.time_period = time_period
        self.n_upcoming_periods = n_upcoming_periods

        self.events_per_employee = events_per_employee

    @property
    def is_month_period(self):
        return self.time_period == "month"

    def calculate_period_key(self, period_start):
        if self.is_month_period:
            return period_start.strftime("%b")
        else:
            return period_start.isocalendar()[1]

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

                employee_data_events = process_employees_events(
                    {employee: employee_events}, **{self.time_period: period_start}
                )[employee.name]

                for event_data in employee_data_events.events:
                    projects_total[employee.name][event_data["project_id"]] += event_data["duration"]

                events[employee.name][period_key] = {
                    "availability": available_time_of_employee(
                        employee, employee_events, period_start, period_end
                    ),
                    "projects": employee_data_events.events,
                }

            events[employee.name]["projects_total"] = self.calculate_total_projects(employee, projects_total)

        return events
