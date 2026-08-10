import datetime

from django.test import TestCase

from white_rabbit.events import get_event_data
from white_rabbit.models import Category, Project
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.tests.factory import CompanyFactory, EmployeeFactory


class TestGetEventData(TestCase):
    def setUp(self):
        self.company = CompanyFactory()
        self.employee = EmployeeFactory(company=self.company)
        self.start = datetime.datetime(2022, 1, 3, 9, 0)

    def get_event_data(self, calendar_name, start=None, end=None):
        start = start or self.start
        end = end or start + datetime.timedelta(hours=2)
        return get_event_data(
            start, end, calendar_name, ProjectFinder(), self.employee
        )

    def test_without_subproject(self):
        project = Project.objects.create(company=self.company, name="P1")

        event = self.get_event_data("P1")

        self.assertEqual(event["project_id"], project.pk)
        self.assertEqual(event["project_name"], "P1")
        self.assertEqual(event["name"], "P1")
        self.assertIsNone(event["subproject_name"])
        self.assertIsNone(event["category"])
        self.assertEqual(event["start_datetime"], self.start)
        self.assertEqual(event["end_datetime"], self.start + datetime.timedelta(hours=2))
        self.assertEqual(event["duration"], 2)

    def test_with_subproject(self):
        project = Project.objects.create(company=self.company, name="P1")

        for calendar_name in ["P1 [dev]", "P1[dev]", "P1  [dev]"]:
            with self.subTest(calendar_name=calendar_name):
                event = self.get_event_data(calendar_name)
                self.assertEqual(event["project_id"], project.pk)
                self.assertEqual(event["name"], "P1")
                self.assertEqual(event["subproject_name"], "dev")

    def test_subproject_name_is_normalized(self):
        Project.objects.create(company=self.company, name="P1")

        event = self.get_event_data("P1 [ Développement ]")

        self.assertEqual(event["subproject_name"], "developpement")

    def test_empty_subproject(self):
        Project.objects.create(company=self.company, name="P1")

        event = self.get_event_data("P1 []")

        self.assertEqual(event["name"], "P1")
        self.assertEqual(event["subproject_name"], "")

    def test_unclosed_bracket_is_part_of_project_name(self):
        event = self.get_event_data("P1 [dev")

        self.assertEqual(event["name"], "P1 [dev")
        self.assertIsNone(event["subproject_name"])

    def test_category_is_returned(self):
        category = Category.objects.create(name="Interne", company=self.company)
        Project.objects.create(company=self.company, name="P1", category=category)

        event = self.get_event_data("P1")

        self.assertEqual(event["category"], "Interne")

    def test_unknown_project_is_created(self):
        event = self.get_event_data("New project [dev]")

        project = Project.objects.get(company=self.company, name="New Project")
        self.assertEqual(event["project_id"], project.pk)
        self.assertEqual(event["project_name"], "New Project")
        self.assertEqual(event["subproject_name"], "dev")

    def test_duration_is_capped_to_default_working_hours(self):
        Project.objects.create(company=self.company, name="P1")

        event = self.get_event_data(
            "P1", end=self.start + datetime.timedelta(hours=12)
        )

        self.assertEqual(event["duration"], 8)
