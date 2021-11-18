from white_rabbit.models import Project, Alias, Company


def get_key(name: str, company_name: str):
    return f"{name.lower()}__{company_name}"


class ProjectNameFinder:
    def __init__(self):
        self.cache = {}
        for name, lowercase_name, company_name in Project.objects.values_list(
            "name", "lowercase_name", "company__name"
        ).all():
            key = get_key(lowercase_name, company_name)
            self.cache[key] = name
        for lowercase_name, name, company_name in Alias.objects.values_list(
            "lowercase_name", "project__name", "project__company__name"
        ).all():
            key = get_key(lowercase_name, company_name)
            self.cache[key] = name

    def get_project_name(self, name: str, company: Company):
        name = name.strip()
        key = get_key(name, company.name)
        if key not in self.cache:
            Project.objects.create(name=name, company=company)
            self.cache[key] = name
            return name

        return self.cache[key]


def is_full_uppercase(name: str) -> bool:
    return name == name.upper()
