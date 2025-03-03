import datetime
from collections import defaultdict
from typing import Union, Dict, Any

from white_rabbit.models import Project, Company
from white_rabbit.text_utils import normalize_name


class ProjectFinder:
    def __init__(self):
        print("#### ProjectFinder init")
        self.all_projects = Project.objects.prefetch_related("company", "aliases").all()
        self.projects_with_dates = list(
            self.all_projects.filter(start_date__isnull=False, end_date__isnull=False)
        )
        self.project_with_only_start_date = list(
            self.all_projects.filter(start_date__isnull=False, end_date__isnull=True)
        )
        self.project_without_dates = list(
            self.all_projects.filter(start_date__isnull=True, end_date__isnull=True)
        )
        self.temp_one_project_per_company = {}
        self.projects_for_matching_per_company = {}
        # sorted names per company
        self.sorted_names_per_company = {}
        self.sorted_projects_pks_per_company = {}
        # Dictionary mapping companies to normalized names to lists of projects
        self.projects_for_normalized_name_per_company = defaultdict(
            lambda: defaultdict(list)
        )

    def populate_projects_for_normalized_name_per_company(self, company: Company):
        """
        Populate the projects_for_normalized_name_per_company dictionary for a given company.
        """
        for project in self.get_projects_for_matching(company):
            # Add project under its own normalized name
            normalized_name = normalize_name(project.name)
            self.projects_for_normalized_name_per_company[company][
                normalized_name
            ].append(project)

            # Add project under each of its aliases' normalized names
            for alias in project.aliases.all():
                normalized_alias = normalize_name(alias.name)
                self.projects_for_normalized_name_per_company[company][
                    normalized_alias
                ].append(project)

    def get_project_names_for_company(self, company: Company):
        if company in self.sorted_names_per_company:
            return self.sorted_names_per_company[company]

        self.sorted_names_per_company[company] = []
        self.sorted_projects_pks_per_company[company] = []
        for project in self.all_projects:
            if project.company != company:
                continue
            for names in [project.lowercase_name] + [
                alias.lowercase_name for alias in project.aliases.all()
            ]:
                self.sorted_names_per_company[company] += names
                self.sorted_projects_pks_per_company[company] += [project.pk] * len(
                    names
                )

        # sort by name
        self.sorted_projects_pks_per_company[company] = [
            project_pk
            for _, project_pk in sorted(
                zip(
                    self.sorted_names_per_company[company],
                    self.sorted_projects_pks_per_company[company],
                )
            )
        ]

        return self.sorted_names_per_company[company]

    def get_projects_for_matching(self, company: Company):
        """
        We first want to match with projects that have both start and end dates,
        then with projects that have only a start date,
        and finally with projects that have no dates.
        """
        if company in self.projects_for_matching_per_company:
            return self.projects_for_matching_per_company[company]

        def filter_projects_by_company(projects, company):
            return [project for project in projects if project.company == company]

        to_return = (
            filter_projects_by_company(self.projects_with_dates, company)
            + filter_projects_by_company(self.project_with_only_start_date, company)
            + filter_projects_by_company(self.project_without_dates, company)
        )
        self.projects_for_matching_per_company[company] = to_return
        return to_return

    def create_project(self, name: str, company: Company):
        name = name.strip()
        if not is_full_uppercase(name):
            name = name.title()

        project = Project.objects.create(name=name, company=company)
        self.project_without_dates.append(project)
        return project

    def get_project(
        self, name: str, company: Company, date: Union[datetime.date, None]
    ):
        """
        Find a project by name, company, and date using the projects_for_normalized_name_per_company dictionary.
        This method is much faster as it uses direct dictionary lookup and pre-filters by company.
        """
        if not len(self.projects_for_normalized_name_per_company[company]):
            self.populate_projects_for_normalized_name_per_company(company)
        name = name.strip()
        if not is_full_uppercase(name):
            name = name.title()

        # Convert datetime to date if needed
        if isinstance(date, datetime.datetime):
            date = date.date()

        # Get the normalized name for lookup
        normalized_name = normalize_name(name)

        # Look up projects with this normalized name for this company
        candidate_projects = self.projects_for_normalized_name_per_company.get(
            company, {}
        ).get(normalized_name, [])

        # Filter projects by date
        for project in candidate_projects:
            if self.project_corresponds(project, name, date):
                return project

        # No matching project found, create a new one
        return self.create_project(name, company)

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
        normalized_name = normalize_name(name)
        for project_name in names:
            if project_name == normalized_name:
                return True

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
