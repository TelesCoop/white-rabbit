from django.test import TestCase

from white_rabbit.models import Company
from white_rabbit.views import day_distribution


class DayDistributionTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        self.company = Company.objects.create(name="Test")
        super().__init__(*args, **kwargs)

    def test_day_distribution_single_project_full_day(self):
        self.assertEqual(
            day_distribution(
                [
                    {
                        "name": "a",
                        "duration": self.company.min_working_hours_for_full_day,
                    }
                ],
                company=self.company,
            ),
            {"a": 1},
        )
        self.assertEqual(
            day_distribution(
                [
                    {
                        "name": "a",
                        "duration": self.company.min_working_hours_for_full_day + 2,
                    }
                ],
                company=self.company,
            ),
            {"a": 1},
        )

    def test_day_distribution_single_project_unfinished_day(self):
        self.assertEqual(
            day_distribution(
                [
                    {
                        "name": "a",
                        "duration": self.company.min_working_hours_for_full_day - 1,
                    }
                ],
                company=self.company,
            ),
            {
                "a": (self.company.min_working_hours_for_full_day - 1)
                / self.company.default_day_working_hours
            },
        )

    def test_day_distribution_multiple_projects(self):
        self.assertEqual(
            day_distribution(
                [
                    {"name": "a", "duration": 10},
                    {"name": "b", "duration": 10},
                ],
                company=self.company,
            ),
            {"a": 0.5, "b": 0.5},
        )
        events = [
            {"name": "a", "duration": self.company.min_working_hours_for_full_day / 3},
            {
                "name": "b",
                "duration": 2 * self.company.min_working_hours_for_full_day / 3 + 1,
            },
        ]
        duration_a = events[0]["duration"]
        duration_b = events[1]["duration"]
        self.assertEqual(
            day_distribution(events, company=self.company),
            {
                "a": duration_a / (duration_a + duration_b),
                "b": duration_b / (duration_a + duration_b),
            },
        )
