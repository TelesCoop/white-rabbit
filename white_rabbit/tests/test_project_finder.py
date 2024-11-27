import datetime

from django.test import TestCase

from white_rabbit.models import Project
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.tests.factory import CompanyFactory


class TestProjectNameFinder(TestCase):
    def test_simple_case(self):
        company = CompanyFactory()
        p1 = Project.objects.create(company=company, name="P1")
        Project.objects.create(company=company, name="p2")
        project_finder = ProjectFinder()
        self.assertEqual(project_finder.get_project("p1", company, None), p1)
        self.assertEqual(project_finder.get_project("P1", company, None), p1)

        # no corresponding name creates new project
        p3 = project_finder.get_project("P3", company, None)
        self.assertEqual(p3.name, "P3")

    def test_aliases(self):
        company = CompanyFactory()
        p1 = Project.objects.create(company=company, name="P1")
        Project.objects.create(company=company, name="p2")
        p1.aliases.create(name="alias")
        project_finder = ProjectFinder()
        self.assertEqual(project_finder.get_project("alias", company, None), p1)

    def test_date(self):
        """
        Test that if a project exists both without dates and with dates,
        the one with dates is returned, if there is one corresponding.
        """
        company = CompanyFactory()
        p1 = Project.objects.create(company=company, name="P1")
        p1_2020 = Project.objects.create(
            company=company, name="P1", start_date="2020-01-01", end_date="2020-12-31"
        )
        project_finder = ProjectFinder()
        self.assertEqual(
            project_finder.get_project("p1", company, datetime.date(2019, 1, 1)), p1
        )
        self.assertEqual(
            project_finder.get_project("p1", company, datetime.date(2020, 1, 1)),
            p1_2020,
        )
        self.assertEqual(
            project_finder.get_project("p1", company, datetime.date(2021, 1, 1)), p1
        )

        # test creation order has no effect
        p2_2020 = Project.objects.create(
            company=company, name="P2", start_date="2020-01-01", end_date="2020-12-31"
        )
        p2 = Project.objects.create(company=company, name="P2")
        project_finder = ProjectFinder()
        self.assertEqual(
            project_finder.get_project("p2", company, datetime.date(2019, 1, 1)), p2
        )
        self.assertEqual(
            project_finder.get_project("p2", company, datetime.date(2020, 1, 1)),
            p2_2020,
        )
        self.assertEqual(
            project_finder.get_project("p2", company, datetime.date(2021, 1, 1)), p2
        )

        # test having both start AND end dates corresponding has priority
        p3_2020_plus = Project.objects.create(
            company=company, name="P3", start_date="2020-01-01", end_date=None
        )
        p3_2020 = Project.objects.create(
            company=company, name="P3", start_date="2020-01-01", end_date="2020-12-31"
        )
        project_finder = ProjectFinder()
        self.assertEqual(
            project_finder.get_project("p3", company, datetime.date(2020, 1, 1)),
            p3_2020,
        )
        self.assertEqual(
            project_finder.get_project("p3", company, datetime.date(2021, 1, 1)),
            p3_2020_plus,
        )
