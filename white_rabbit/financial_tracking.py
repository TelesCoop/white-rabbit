from typing import Dict

from white_rabbit.models import Project


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
    return (
        project.end_date
        and project.category
        and "client" in project.category.name.lower()
    )


def calculate_financial_indicators(company, identifier_order, total_by_project_id):
    projects_by_id = {
        project.pk: project for project in Project.objects.filter(company=company)
    }

    projects_data: Dict[str, Dict[str, int]] = {}
    totals: Dict[str, Dict[str, int]] = {
        "total_below_real_cost": create_total(),
        "total_below_profitability_threshold": create_total(),
    }

    for project_id in identifier_order:
        try:
            project = projects_by_id[project_id]
        except KeyError:
            # can happen if project is missing in cache
            continue
        if not is_pertinent_evaluate_monetarily(project):
            continue

        projects_data[project_id] = {
            "total_sold": project.total_sold,
            "estimated_days_count": project.estimated_days_count,
            "done": (done := total_by_project_id[project_id]),
            "real_cost": done * float(project.company.daily_employee_cost),
            "profitability_threshold": done
            * float(project.company.profitability_threshold),
            "opportunity_cost": done * float(project.company.daily_market_price),
            "tjm_reel": (
                float(project.total_sold) / done if project.total_sold and done else 0
            ),
            "id": project_id,
            "name": project.name,
            "start_date": (
                project.start_date.strftime("%m/%y") if project.start_date else ""
            ),
            "end_date": project.end_date.strftime("%m/%y"),
        }
        add_project_to_totals(projects_data[project_id], totals)

    return {
        "projects_data": projects_data,
        "total_below_real_cost": totals["total_below_real_cost"],
        "total_below_profitability_threshold": totals[
            "total_below_profitability_threshold"
        ],
    }
