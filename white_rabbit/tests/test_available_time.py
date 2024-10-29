from datetime import datetime, date

from django.test import TestCase
from white_rabbit.available_time import available_time_of_employee
from white_rabbit.tests.factory import EmployeeFactory


class TestAvailableTime(TestCase):

    def test_busy_all_working_hours_in_the_given_period(self):
        employee = EmployeeFactory()
        events = [
            {
                "project_id": 1,
                "category": "Test Category",
                "name": "Test Project",
                "subproject_name": "Test Subproject",
                "start_datetime": datetime(2022, 1, 1, 9, 0),
                "end_datetime": datetime(2022, 1, 1, 17, 0),
                "duration": 8,
            },
            {
                "project_id": 2,
                "category": "Test Category",
                "name": "Test Project 2",
                "subproject_name": "Test Subproject 2",
                "start_datetime": datetime(2022, 1, 2, 9, 0),
                "end_datetime": datetime(2022, 1, 2, 17, 0),
                "duration": 8,
            },
            {
                "project_id": 3,
                "category": "Test Category",
                "name": "Test Project 2",
                "subproject_name": "Test Subproject 2",
                "start_datetime": datetime(2022, 1, 3, 9, 0),
                "end_datetime": datetime(2022, 1, 3, 17, 0),
                "duration": 8,
            },
        ]
        start_datetime = date(2022, 1, 1)
        end_datetime = date(2022, 1, 3)

        available_time = available_time_of_employee(employee, events, start_datetime, end_datetime)
        expected = 0  # As the employee is busy all the working hours in the given period
        assert available_time == expected

    def test_employee_not_busy_at_all(self):
        employee = EmployeeFactory()
        events = []
        start_datetime = date(2024, 3, 4)
        end_datetime = date(2024, 3, 8)

        available_time = available_time_of_employee(employee, events, start_datetime, end_datetime)
        assert available_time == 5

    def test_compute_available_time_with_weekend(self):
        start_datetime = date(2024, 3, 11)
        end_datetime = date(2024, 3, 25)
        employee = EmployeeFactory()
        available_time = available_time_of_employee(employee, [], start_datetime, end_datetime)
        assert available_time == 11

    def test_compute_available_time_for_half_busy_employee(self):
        start_datetime = date(2024, 3, 4)
        end_datetime = date(2024, 3, 8)
        employee = EmployeeFactory()
        events = [
            {
                "project_id": 1,
                "category": "Test Category",
                "name": "Test Project",
                "subproject_name": "Test Subproject",
                "start_datetime": datetime(2024, 3, 4, 9, 0),
                "end_datetime": datetime(2024, 3, 4, 17, 0),
                "duration": 4,
            },
            {
                "project_id": 2,
                "category": "Test Category",
                "name": "Test Project 2",
                "subproject_name": "Test Subproject 2",
                "start_datetime": datetime(2024, 3, 5, 9, 0),
                "end_datetime": datetime(2024, 3, 5, 17, 0),
                "duration": 8,
            },
        ]
        available_time = available_time_of_employee(employee, events, start_datetime, end_datetime)
        assert available_time == 3.5

    def test_compute_available_time_with_public_holidays(self):
        start_datetime = date(2024, 5, 1)
        end_datetime = date(2024, 5, 3)
        employee = EmployeeFactory()
        available_time = available_time_of_employee(employee, [], start_datetime, end_datetime)
        assert available_time == 2
