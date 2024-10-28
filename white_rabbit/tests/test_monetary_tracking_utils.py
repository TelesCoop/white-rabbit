from datetime import datetime

from white_rabbit.tests.factory import CompanyFactory, ProjectFactory
from white_rabbit.utils.monetary_tracking import calculate_monetary_figures


def test_calculate_monetary_figures():
    company = CompanyFactory()
    project_1 = ProjectFactory(
        company=company,
        name="Project sous le coût réel",
        category="CLIENT",
        total_sold=1000,
    )
    project_2 = ProjectFactory(
        company=company,
        name="Project sous le seuil de rentabilité",
        category="CLIENT",
        total_sold=2000,
    )
    project_3 = ProjectFactory(
        company=company,
        name="Project 2 sous le seuil de rentabilité",
        category="CLIENT",
        total_sold=2500,
    )
    project_4 = ProjectFactory(
        company=company,
        name="Project rentable",
        category="CLIENT",
        total_sold=7000,
    )
    days_done = 8
    monetary_figures = calculate_monetary_figures(
        company, 
        ["1", "2", "3", "4"], 
        {
			project.pk: days_done for project in [project_1, project_2, project_3, project_4]
		}
    )
    assert monetary_figures == {
        "projects_data": {
            project.pk: {
                "total_sold": project.total_sold,
                "estimated_days_count": project.estimated_days_count,
                "done": days_done,
                "real_cost": 1600,
                "profitability_threshold": 3200,
                "opportunity_cost": 4800,
                "id": project.pk,
                "name": project.name,
                "start_date": project.start_date.strftime('%m/%y'),
                "end_date": project.end_date.strftime('%m/%y'),
			} for project in [project_1, project_2, project_3, project_4]
		},
        # Project 1
        "total_below_real_cost": 
			{
			"total_sold": 1000,
			"real_cost": 1600,
			"profitability_threshold": 3200,
			"opportunity_cost": 4800,
		},
        # Project 2 + project 3
        "total_below_profitability_threshold": {
			"total_sold": 4500,
			"real_cost": 3200,
			"profitability_threshold": 6400,
			"opportunity_cost": 9600,
		},
	}
