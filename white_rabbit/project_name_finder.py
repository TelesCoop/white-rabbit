import datetime
from typing import Union, Dict, Any

from white_rabbit.models import Project, Company


def get_key(
        name: str, company_name: str, start_datetime: Union[datetime.date, None]
) -> str:
    to_return = f"{name.lower()}__{company_name}"
    if start_datetime:
        to_return += f"__{start_datetime.strftime('%Y-%m-%d')}"

    return to_return


class ProjectFinder:
    def __init__(self):
        self.cache = {}
        self.all_projects = list(
            Project.objects.prefetch_related("company", "aliases").all()
        )

    def get_project(self, name: str, company: Company, date: datetime.date):
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
                names = [project.lowercase_name] + [
                    alias.lowercase_name for alias in project.aliases.all()
                ]
                for project_name in names:
                    if project_name != name.lower():
                        continue
                    if project.company != company:
                        continue
                    if not project.start_date:
                        return project
                    if project.end_date:
                        if project.start_date <= date <= project.end_date:
                            return project
                    else:
                        if project.start_date <= date:
                            return project

        # no project has been found, create a new one
        if key not in self.cache:
            project = Project.objects.create(name=name, company=company)
            self.all_projects.append(project)
            self.cache[key] = project
            return project

        return self.cache[key]

    def by_company(self, company: Company) -> Dict[str, Any]:
        to_return: Dict[str, Any] = {}
        for project in self.all_projects:
            if project.company != company:
                continue

            to_return[project.pk] = {
                "name": project.name,
                "start_date": project.start_date and project.start_date.strftime("%b %y"),
                "end_date": project.end_date and project.end_date.strftime("%b %y"),
                "category": project.category or "Non catégorisé",
            }

        return to_return


def is_full_uppercase(name: str) -> bool:
    return name == name.upper()
