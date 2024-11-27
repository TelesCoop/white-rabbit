import datetime
from typing import Union, Dict, Any

from white_rabbit.models import Project, Company


class ProjectFinder:
    def __init__(self):
        all_projects = Project.objects.prefetch_related("company", "aliases").all()
        self.projects_with_dates = list(
            all_projects.filter(start_date__isnull=False, end_date__isnull=False)
        )
        self.project_with_only_start_date = list(
            all_projects.filter(start_date__isnull=False, end_date__isnull=True)
        )
        self.project_without_dates = list(
            all_projects.filter(start_date__isnull=True, end_date__isnull=True)
        )

    def get_projects_for_matching(self, company: Company):
        """
        We first want to match with projects that have both start and end dates,
        then with projects that have only a start date,
        and finally with projects that have no dates.
        """
        return (
            [
                project
                for project in self.projects_with_dates
                if project.company == company
            ]
            + [
                project
                for project in self.project_with_only_start_date
                if project.company == company
            ]
            + [
                project
                for project in self.project_without_dates
                if project.company == company
            ]
        )

    @staticmethod
    def project_corresponds(project, name, date) -> bool:
        # reject if date does not correspond
        if project.start_date and project.start_date > date:
            return False
        if project.end_date and project.end_date < date:
            return False

        # name corresponds
        names = [project.lowercase_name] + [
            alias.lowercase_name for alias in project.aliases.all()
        ]
        for project_name in names:
            if project_name == name.lower():
                return True

    def get_project(
        self, name: str, company: Company, date: Union[datetime.date, None]
    ):
        name = name.strip()
        if not is_full_uppercase(name):
            name = name.title()

        if isinstance(date, datetime.datetime):
            date = date.date()

        # find project by date
        for project_candidate in self.get_projects_for_matching(company):
            if self.project_corresponds(project_candidate, name, date):
                return project_candidate

        # no project has been found, create a new one
        project = Project.objects.create(name=name, company=company)
        self.project_without_dates.append(project)
        return project

    def by_company(self, company: Company) -> Dict[str, Any]:
        to_return: Dict[str, Any] = {}
        for project in self.get_projects_for_matching(company):
            to_return[project.pk] = {
                "name": project.name,
                "start_date": project.start_date
                and project.start_date.strftime("%b %y"),
                "end_date": project.end_date and project.end_date.strftime("%b %y"),
                "category": project.category
                or {"name": "inconnue", "color": "bg-white-100"},
            }

        return to_return


def is_full_uppercase(name: str) -> bool:
    return name == name.upper()
