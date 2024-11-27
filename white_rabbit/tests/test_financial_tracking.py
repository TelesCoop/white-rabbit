from django.test import TestCase
from white_rabbit.tests.factory import CompanyFactory, ProjectFactory
from white_rabbit.financial_tracking import calculate_financial_indicators


class TestFinancialTracking(TestCase):
    def test_calculate_financial_indicators(self):
        PROJECT_1_SOLD = 1000
        PROJECT_2_SOLD = 2000
        PROJECT_3_SOLD = 2500
        PROJECT_4_SOLD = 7000
        company = CompanyFactory()
        client_category = company.categories.create(name="CLIENT")
        project_1 = ProjectFactory(
            company=company,
            name="Project sous le coût réel",
            category=client_category,
            total_sold=PROJECT_1_SOLD,
        )
        project_2 = ProjectFactory(
            company=company,
            name="Project sous le seuil de rentabilité",
            category=client_category,
            total_sold=PROJECT_2_SOLD,
        )
        project_3 = ProjectFactory(
            company=company,
            name="Project 2 sous le seuil de rentabilité",
            category=client_category,
            total_sold=PROJECT_3_SOLD,
        )
        project_4 = ProjectFactory(
            company=company,
            name="Project rentable",
            category=client_category,
            total_sold=PROJECT_4_SOLD,
        )
        days_done = 8
        financial_indicators = calculate_financial_indicators(
            company,
            [project.pk for project in [project_1, project_2, project_3, project_4]],
            {
                project.pk: days_done
                for project in [project_1, project_2, project_3, project_4]
            },
        )
        one_project_real_cost = days_done * company.daily_employee_cost
        one_project_profitability_threshold = (
            days_done * company.profitability_threshold
        )
        one_project_opportunity_cost = days_done * company.daily_market_price
        self.assertEqual(
            financial_indicators,
            {
                "projects_data": {
                    project.pk: {
                        "total_sold": project.total_sold,
                        "estimated_days_count": project.estimated_days_count,
                        "done": days_done,
                        "real_cost": one_project_real_cost,
                        "profitability_threshold": one_project_profitability_threshold,
                        "opportunity_cost": one_project_opportunity_cost,
                        "id": project.pk,
                        "name": project.name,
                        "start_date": project.start_date.strftime("%m/%y"),
                        "end_date": project.end_date.strftime("%m/%y"),
                    }
                    for project in [project_1, project_2, project_3, project_4]
                },
                # Project 1
                "total_below_real_cost": {
                    "total_sold": PROJECT_1_SOLD,
                    "real_cost": one_project_real_cost,
                    "profitability_threshold": one_project_profitability_threshold,
                    "opportunity_cost": one_project_opportunity_cost,
                },
                # Project 2 + project 3
                "total_below_profitability_threshold": {
                    "total_sold": PROJECT_2_SOLD + PROJECT_3_SOLD,
                    "real_cost": one_project_real_cost * 2,
                    "profitability_threshold": one_project_profitability_threshold * 2,
                    "opportunity_cost": one_project_opportunity_cost * 2,
                },
            },
        )
