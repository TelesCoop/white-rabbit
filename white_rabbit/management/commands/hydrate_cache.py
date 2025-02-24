from django.core.management import BaseCommand

from white_rabbit.events import get_events_from_employees_from_cache
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectFinder


class Command(BaseCommand):
    # add argument for email of employee to update
    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Email of the employee to update",
        )

    def handle(self, *args, **options):
        if options["email"]:
            employees = list(
                Employee.objects.filter(user__email__contains=options["email"])
            )
        else:
            employees = Employee.objects.all()
        project_finder = ProjectFinder()
        get_events_from_employees_from_cache(
            employees, project_finder, force_refresh=True
        )
