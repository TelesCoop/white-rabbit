from datetime import date, datetime
from django.test import TestCase

from white_rabbit.constants import SEVERITY_COLORS
from white_rabbit.models import ProjectCategories
from white_rabbit.templatetags.white_rabbit_tags import (
    number_of_working_days_for_period_key,
    monthly_hours_color,
)
from white_rabbit.utils import (
    filter_events_per_time_period,
    group_events_per_category,
    count_number_days_spent,
    group_events_by_day,
)


class TestUtils(TestCase):
    def test_monthly_colors(self):
        self.assertEqual(number_of_working_days_for_period_key("01-2025"), 23)
        self.assertEqual(number_of_working_days_for_period_key("02-2025"), 20)
        self.assertEqual(monthly_hours_color(20 * 20, "02-2025"), SEVERITY_COLORS[0])
        self.assertEqual(monthly_hours_color(20 * 11, "02-2025"), SEVERITY_COLORS[1])
        self.assertEqual(monthly_hours_color(20 * 5, "02-2025"), SEVERITY_COLORS[-1])

    def test_filter_events_per_month_and_week(self):
        event_01 = {
            "project_id": 1,
            "name": "Project1",
            "subproject_name": None,
            "start_datetime": datetime(2022, 1, 1),
            "duration": 6.0,
        }
        event_02 = {
            "project_id": 1,
            "name": "Project1",
            "subproject_name": None,
            "start_datetime": datetime(2022, 2, 10),
        }
        event_03 = {
            "project_id": 3,
            "name": "Project2",
            "subproject_name": None,
            "start_datetime": datetime(2022, 3, 10),
            "duration": 6.0,
        }
        event_04 = {
            "project_id": 2,
            "name": "Project1",
            "subproject_name": None,
            "start_datetime": datetime(2022, 3, 11),
            "duration": 6.0,
        }
        event_05 = {
            "project_id": 2,
            "name": "Project2",
            "subproject_name": None,
            "start_datetime": datetime(2022, 3, 19),
            "duration": 3.0,
        }
        events = [event_01, event_02, event_03, event_04, event_05]

        event_month_01 = filter_events_per_time_period(
            events, timeperiod=datetime(2022, 1, 1)
        )
        assert len(event_month_01) == 1
        assert event_month_01[0] == event_01

        events_month_3 = filter_events_per_time_period(
            events, timeperiod=datetime(2022, 3, 1)
        )
        assert len(events_month_3) == 3

        events_week_10 = filter_events_per_time_period(
            events, timeperiod_type="week", timeperiod=datetime(2022, 3, 9)
        )
        assert len(events_week_10) == 2
        assert events_week_10[0] == event_03
        assert events_week_10[1] == event_04

        # TODO : Fix this test !!
        # event_week_11 = filter_events_per_time_period(events, timeperiod_type="week", timeperiod=datetime(2022, 3, 13))
        # assert len(event_week_11) == 1
        # assert event_week_11[0] == event_05

        event_month_01 = filter_events_per_time_period(
            events, timeperiod=datetime(2022, 1, 1)
        )
        assert len(event_month_01) == 1
        assert event_month_01[0] == event_01

    def test_count_number_days_spent_per_project_id(self):
        event_01 = {
            "project_id": 1,
            "name": "Project1",
            "subproject_name": None,
            "start_datetime": datetime(2022, 1, 1),
            "duration": 6.0,
            "category": "category",
        }
        event_02 = {
            "project_id": 1,
            "name": "Project1",
            "subproject_name": None,
            "start_datetime": datetime(2022, 2, 10),
            "duration": 3.0,
            "category": "category1",
        }
        event_03 = {
            "project_id": 3,
            "name": "Project2",
            "subproject_name": None,
            "start_datetime": datetime(2022, 3, 10),
            "duration": 6.0,
            "category": "category1",
        }
        number_days_spent_per_project_id = count_number_days_spent(
            [event_01, event_02, event_03],
            lambda event: event["project_id"],
            min_working_hours_for_full_day=6,
        )
        assert number_days_spent_per_project_id == {
            1: {
                "days_spent": 1.5,
                "duration": 9.0,
                "category": "",
                "events": [
                    {
                        "project_id": 1,
                        "name": "Project1",
                        "subproject_name": None,
                        "start_datetime": datetime(2022, 1, 1, 0, 0),
                        "duration": 6.0,
                        "category": "category",
                    },
                    {
                        "project_id": 1,
                        "name": "Project1",
                        "subproject_name": None,
                        "start_datetime": datetime(2022, 2, 10, 0, 0),
                        "duration": 3.0,
                        "category": "category1",
                    },
                ],
            },
            3: {
                "days_spent": 1.0,
                "duration": 6.0,
                "category": "",
                "events": [
                    {
                        "project_id": 3,
                        "name": "Project2",
                        "subproject_name": None,
                        "start_datetime": datetime(2022, 3, 10, 0, 0),
                        "duration": 6.0,
                        "category": "category1",
                    }
                ],
            },
        }

    def test_group_events_per_category(self):
        category = "category1"
        category_2 = "category2"
        events = [
            {
                "project_id": 1,
                "name": "Project1",
                "subproject_name": None,
                "start_datetime": datetime(2022, 1, 1),
                "duration": 6.0,
                "category": category,
            },
            {
                "project_id": 1,
                "name": "Project1",
                "subproject_name": None,
                "start_datetime": datetime(2022, 1, 1),
                "duration": 6.0,
                "category": category,
            },
            {
                "project_id": 2,
                "name": "Project2",
                "subproject_name": None,
                "start_datetime": datetime(2022, 1, 1),
                "duration": 6.0,
                "category": category_2,
            },
            {
                "project_id": 2,
                "name": "Project2",
                "subproject_name": None,
                "start_datetime": datetime(2022, 3, 1),
                "duration": 3.0,
                "category": "",
            },
        ]
        events_per_category = group_events_per_category(events)

        assert len(events_per_category) == 3

        assert category in events_per_category
        assert category_2 in events_per_category
        assert "" in events_per_category

        assert len(events_per_category[category]) == 2
        assert len(events_per_category[category_2]) == 1
        assert len(events_per_category[""]) == 1

        assert events_per_category == {
            "category1": [
                {
                    "project_id": 1,
                    "name": "Project1",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 1, 1, 0, 0),
                    "duration": 6.0,
                    "category": "category1",
                },
                {
                    "project_id": 1,
                    "name": "Project1",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 1, 1, 0, 0),
                    "duration": 6.0,
                    "category": "category1",
                },
            ],
            "category2": [
                {
                    "project_id": 2,
                    "name": "Project2",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 1, 1, 0, 0),
                    "duration": 6.0,
                    "category": "category2",
                }
            ],
            "": [
                {
                    "project_id": 2,
                    "name": "Project2",
                    "subproject_name": None,
                    "start_datetime": datetime(2022, 3, 1, 0, 0),
                    "duration": 3.0,
                    "category": "",
                }
            ],
        }

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
