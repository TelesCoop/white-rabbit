import datetime
from typing import Union, Dict, Any

from white_rabbit.models import Project, Alias, Company


def get_key(
    name: str, company_name: str, start_date: Union[datetime.date, None]
) -> str:
    to_return = f"{name.lower()}__{company_name}"
    if start_date:
        to_return += f"__{start_date.strftime('%Y-%m-%d')}"

    return to_return


class ProjectNameFinder:
    def __init__(self):
        self.cache = {}
        self.all_projects = list(Project.objects.prefetch_related("company").all())
        for project in self.all_projects:
            key = get_key(
                project.lowercase_name, project.company.name, project.start_date
            )
            self.cache[key] = project.pk
        for lowercase_name, pk, company_name, start_date in Alias.objects.values_list(
            "lowercase_name",
            "project__pk",
            "project__company__name",
            "project__start_date",
        ).all():
            key = get_key(lowercase_name, company_name, start_date)
            self.cache[key] = pk

    def get_project_id(self, name: str, company: Company, date: datetime.date):
        name = name.strip()
        if not is_full_uppercase(name):
            name = name.title()

        # find project by date
        key = get_key(name, company.name, None)
        if key in self.cache:
            # if a project has no start date and same name, it will be found in cache
            return self.cache[key]
        else:
            for project in self.all_projects:
                if project.lowercase_name != name.lower():
                    continue
                if not project.start_date:
                    return project.pk
                if project.end_date:
                    if project.start_date <= date <= project.end_date:
                        return project.pk
                else:
                    if project.start_date <= date:
                        return project.pk

        # no project has been found, create a new one
        if key not in self.cache:
            project = Project.objects.create(name=name, company=company)
            self.all_projects.append(project)
            self.cache[key] = project.pk
            return project.pk

        return self.cache[key]

    def projects_for_company(self, company: Company) -> Dict[str, Any]:
        to_return: Dict[str, Any] = {}
        for project in self.all_projects:
            if project.company != company:
                continue

            to_return[project.pk] = {
                "name": project.name,
                "start_date": project.start_date
                and project.start_date.strftime("%b %y"),
                "end_date": project.end_date and project.end_date.strftime("%b %y"),
            }

        return to_return


def is_full_uppercase(name: str) -> bool:
    return name == name.upper()
