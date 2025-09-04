import datetime

from django.views.generic import TemplateView

from white_rabbit.events import (
    EventsPerEmployee,
    get_events_from_employees_from_cache,
    employees_for_user,
)
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.state_of_day import (
    state_of_days_per_employee_for_week,
)


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
