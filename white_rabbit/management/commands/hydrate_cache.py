from django.core.management import BaseCommand

from white_rabbit.events import get_events_from_employees_from_cache
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectFinder


class Command(BaseCommand):
    def handle(self, *args, **options):
        employees = Employee.objects.all()
        project_finder = ProjectFinder()
        get_events_from_employees_from_cache(employees, project_finder)
