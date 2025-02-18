from datetime import date, datetime

from django.test import TestCase

from white_rabbit.constants import SEVERITY_COLORS
from white_rabbit.models import ProjectCategories
from white_rabbit.templatetags.white_rabbit_tags import (
    number_of_working_days_for_period_key,
    monthly_hours_color,
)
from white_rabbit.utils import group_events_by_day


class TestUtils(TestCase):
    def test_monthly_colors(self):
        self.assertEqual(number_of_working_days_for_period_key("01-2025"), 23)
        self.assertEqual(number_of_working_days_for_period_key("02-2025"), 20)
        self.assertEqual(monthly_hours_color(20 * 20, "02-2025"), SEVERITY_COLORS[0])
        self.assertEqual(monthly_hours_color(20 * 11, "02-2025"), SEVERITY_COLORS[1])
        self.assertEqual(monthly_hours_color(20 * 5, "02-2025"), SEVERITY_COLORS[-1])

    def test_group_events_by_day(self):
        events = [
            {
                "project_id": 1,
                "name": "Project",
                "subproject_name": None,
                "start_datetime": datetime(2022, 1, 1),
                "category": ProjectCategories.PRO_BONO.value,
                "duration": 2.0,
            },
            {
                "project_id": 2,
                "name": "Project_2",
                "subproject_name": None,
                "start_datetime": datetime(2022, 1, 2),
                "duration": 3.0,
                "category": ProjectCategories.PRO_BONO.value,
            },
            {
                "project_id": 3,
                "name": "Project_3",
                "subproject_name": None,
                "start_datetime": datetime(2022, 1, 1),
                "category": ProjectCategories.CLIENT.value,
                "duration": 1.0,
            },
            {
                "project_id": 4,
                "name": "Project_4",
                "subproject_name": None,
                "start_datetime": datetime(2022, 3, 1),
                "category": ProjectCategories.CLIENT.value,
                "duration": 1.0,
            },
        ]
        events_per_day = group_events_by_day(events)
        assert len(events_per_day) == 3

        assert events_per_day == {
            date(2022, 1, 1): [
                {
                    "project_id": 3,
                    "name": "Project_3",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 1, 1, 0, 0),
                    "category": "CLIENT",
                    "duration": 1.0,
                }
            ],
            date(2022, 1, 2): [
                {
                    "project_id": 2,
                    "name": "Project_2",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 1, 2, 0, 0),
                    "duration": 3.0,
                    "category": "PRO_BONO",
                }
            ],
            date(2022, 3, 1): [
                {
                    "project_id": 4,
                    "name": "Project_4",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 3, 1, 0, 0),
                    "category": "CLIENT",
                    "duration": 1.0,
                }
            ],
        }
