from django.test import TestCase

from white_rabbit.tests.factory import EmployeeFactory, EventFactory
from white_rabbit.utils import day_distribution


class TestProjectDuration(TestCase):
    def test_day_distribution_total(self):
        day_employee = EmployeeFactory.create()
        paid_hourly_employee = EmployeeFactory.create(
            is_paid_hourly=True, default_day_working_hours=8
        )

        events = [EventFactory(duration=3), EventFactory(duration=5)]
        res = day_distribution(events, day_employee)
        self.assertAlmostEqual(sum(el["duration"] for el in res.values()), 1)
        res = day_distribution(events, paid_hourly_employee)
        self.assertAlmostEqual(sum(el["duration"] for el in res.values()), 1)

        events = [
            EventFactory(duration=3),
            EventFactory(duration=5),
            EventFactory(duration=4),
        ]
        res = day_distribution(events, day_employee)
        self.assertAlmostEqual(sum(el["duration"] for el in res.values()), 1)
        res = day_distribution(events, paid_hourly_employee)
        self.assertAlmostEqual(sum(el["duration"] for el in res.values()), 1.5)

    def test_day_distribution_subprojects_same_day(self):
        employee = EmployeeFactory.create()
        events = [
            EventFactory(
                project_id=1, project_name="Project", duration=2, subproject_name="a"
            ),
            EventFactory(
                project_id=1, project_name="Project", duration=6, subproject_name="b"
            ),
        ]
        res = day_distribution(events, employee)
        self.assertDictEqual(
            res, {1: {"duration": 1, "details": {"a": 0.25, "b": 0.75}}}
        )
