from django.contrib.auth.models import User
from django.test import TestCase

from white_rabbit.models import Company, Employee
from white_rabbit.views import count_number_days_spent_per_project


class DayDistributionTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        company = Company.objects.create(name="Test")
        user = User.objects.create(username="test")
        self.employee = Employee.objects.create(
            user=user, calendar_ical_url="calendar", company=company
        )
        super().__init__(*args, **kwargs)

    def test_count_number_days_spent_per_project_single_project_full_day(self):
        self.assertEqual(
            count_number_days_spent_per_project(
                [
                    {
                        "name": "a",
                        "duration": self.employee.min_working_hours_for_full_day,
                    }
                ],
                employee=self.employee,
            ),
            {"a": 1},
        )
        self.assertEqual(
            count_number_days_spent_per_project(
                [
                    {
                        "name": "a",
                        "duration": self.employee.min_working_hours_for_full_day + 2,
                    }
                ],
                employee=self.employee,
            ),
            {"a": 1},
        )

    def test_count_number_days_spent_per_project_single_project_unfinished_day(self):
        self.assertEqual(
            count_number_days_spent_per_project(
                [
                    {
                        "name": "a",
                        "duration": self.employee.min_working_hours_for_full_day - 1,
                    }
                ],
                employee=self.employee,
            ),
            {
                "a": (self.employee.min_working_hours_for_full_day - 1)
                     / self.employee.default_day_working_hours
            },
        )

    def test_count_number_days_spent_per_project_multiple_projects(self):
        self.assertEqual(
            count_number_days_spent_per_project(
                [
                    {"name": "a", "duration": 10},
                    {"name": "b", "duration": 10},
                ],
                employee=self.employee,
            ),
            {"a": 0.5, "b": 0.5},
        )
        events = [
            {"name": "a", "duration": self.employee.min_working_hours_for_full_day / 3},
            {
                "name": "b",
                "duration": 2 * self.employee.min_working_hours_for_full_day / 3 + 1,
            },
        ]
        duration_a = events[0]["duration"]
        duration_b = events[1]["duration"]
        self.assertEqual(
            count_number_days_spent_per_project(events, employee=self.employee),
            {
                "a": duration_a / (duration_a + duration_b),
                "b": duration_b / (duration_a + duration_b),
            },
        )
