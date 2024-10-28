from typing import Dict
from white_rabbit.models import Project, ProjectCategories


def create_total():
    return {
        "total_sold": 0,
        "real_cost": 0,
        "profitability_threshold": 0,
        "opportunity_cost": 0,
    }


def add_project_to_total(project, total):
    total["total_sold"] += project["total_sold"]
    total["real_cost"] += project["real_cost"]
    total["profitability_threshold"] += project["profitability_threshold"]
    total["opportunity_cost"] += project["opportunity_cost"]


def add_project_to_totals(project, totals):
    if project["total_sold"] < project["real_cost"]:
        add_project_to_total(project, totals["total_below_real_cost"])
    elif project["total_sold"] < project["profitability_threshold"]:
        add_project_to_total(project, totals["total_below_profitability_threshold"])


def is_pertinent_evaluate_monetarily(project):
    return project.end_date and project.category == ProjectCategories.CLIENT.value


def add_monetary_figures_to_context(context, company):
    projects_by_id = {
        project.pk: project
        for project in Project.objects.filter(
            company=company
        )
    }

    projects_data: Dict[str, Dict[str, int]] = {}
    totals: Dict[str, Dict[str, int]]  = {
        "total_below_real_cost": create_total(),
        "total_below_profitability_threshold": create_total(),
    }

    for project_id in context["identifier_order"]:
        project = projects_by_id[project_id]
        if is_pertinent_evaluate_monetarily(project):
            projects_data[project_id] = {
                "total_sold": project.total_sold,
                "estimated_days_count": project.estimated_days_count,
                "done": (done := context["total_per_identifier"][project_id]),
                "real_cost": done * float(project.company.daily_employee_cost),
                "profitability_threshold": done * float(project.company.profitability_threshold),
                "opportunity_cost": done * float(project.company.daily_market_price),
                "id": project_id,
                "name": project.name,
                "start_date": project.start_date.strftime('%m/%y') if project.start_date else "",
                "end_date": project.end_date.strftime('%m/%y'),
            }
            add_project_to_totals(projects_data[project_id], totals)

    context["projects_data"] = projects_data
    context["daily_employee_cost"] = int(company.daily_employee_cost)
    context["profitability_threshold"] = int(company.profitability_threshold)
    context["daily_market_price"] = int(company.daily_market_price)
    context["total_below_real_cost"] = totals["total_below_real_cost"]
    context["total_below_profitability_threshold"] = totals["total_below_profitability_threshold"]
    
    return context