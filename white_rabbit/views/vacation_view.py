import datetime

from django.views.generic import TemplateView

from white_rabbit.events import get_events_from_employees_from_cache
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.vacation import compute_vacation_summary


class VacationView(TemplateView):
    template_name = "pages/vacation.html"

    def get_context_data(self, **kwargs):
        company = self.request.user.employee.company
        employees = list(
            company.employees.filter(
                start_time_tracking_from__isnull=False,
                disabled=False,
            )
        )
        project_finder = ProjectFinder()
        events_per_employee = get_events_from_employees_from_cache(
            employees, project_finder, request=self.request
        )
        today = datetime.date.today()
        vacation_data = {
            employee.name: compute_vacation_summary(employee, events, today)
            for employee, events in events_per_employee.items()
        }
        return {"vacation_data": vacation_data}
