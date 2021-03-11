from django.test import TestCase

from projects_dashboard.constants import (
    MIN_WORKING_HOURS_FOR_FULL_DAY,
    DEFAULT_DAY_WORKING_HOURS,
)
from projects_dashboard.views import day_distribution


class DayDistributionTestCase(TestCase):
    def test_day_distribution_single_project_full_day(self):
        self.assertEqual(
            day_distribution(
                [{"name": "a", "duration": MIN_WORKING_HOURS_FOR_FULL_DAY}]
            ),
            {"a": 1},
        )
        self.assertEqual(
            day_distribution(
                [{"name": "a", "duration": MIN_WORKING_HOURS_FOR_FULL_DAY + 2}]
            ),
            {"a": 1},
        )

    def test_day_distribution_single_project_unfinished_day(self):
        self.assertEqual(
            day_distribution(
                [{"name": "a", "duration": MIN_WORKING_HOURS_FOR_FULL_DAY - 1}]
            ),
            {"a": (MIN_WORKING_HOURS_FOR_FULL_DAY - 1) / DEFAULT_DAY_WORKING_HOURS},
        )

    def test_day_distribution_multiple_projects(self):
        self.assertEqual(
            day_distribution(
                [
                    {"name": "a", "duration": 10},
                    {"name": "b", "duration": 10},
                ]
            ),
            {"a": 0.5, "b": 0.5},
        )
        events = [
            {"name": "a", "duration": MIN_WORKING_HOURS_FOR_FULL_DAY / 3},
            {"name": "b", "duration": 2 * MIN_WORKING_HOURS_FOR_FULL_DAY / 3 + 1},
        ]
        duration_a = events[0]["duration"]
        duration_b = events[1]["duration"]
        self.assertEqual(
            day_distribution(events),
            {
                "a": duration_a / (duration_a + duration_b),
                "b": duration_b / (duration_a + duration_b),
            },
        )
