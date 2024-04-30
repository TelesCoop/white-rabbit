import pytest
from datetime import date
from white_rabbit.events import EmployeeEvents, Event, count_number_days_spent_per_project
from white_rabbit.tests.factory import EmployeeFactory


class TestEmployeeEvents:
    @pytest.fixture
    def event_instance(self, db):
        employee = EmployeeFactory()
        events = [
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'day': date(2022, 1, 1), 'duration': 2.0},
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'day': date(2022, 1, 2), 'duration': 3.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'day': date(2022, 1, 1), 'duration': 1.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'day': date(2022, 3, 1), 'duration': 1.0},
        ]
        return EmployeeEvents(employee, events)

    def test_events_per_day(self, event_instance):
        events_per_day = event_instance.events_per_day
        assert len(events_per_day) == 3
        assert events_per_day == {
            date(2022, 1, 1): [
                {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'day': date(2022, 1, 1),
                 'duration': 1.0}
            ],
            date(2022, 1, 2): [
                {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'day': date(2022, 1, 2),
                 'duration': 3.0}
            ],
            date(2022, 3, 1): [
                {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'day': date(2022, 3, 1),
                 'duration': 1.0}
            ]
        }

    def test_filter_events_per_month(self, event_instance):
        date_to_find = date(2022, 1, 1)
        events_per_month = event_instance.filter_events_per_month(date_to_find)
        assert len(events_per_month[date_to_find]) == 3

    def test_group_events_per_project(self, event_instance):
        events = [
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'day': date(2022, 1, 1), 'duration': 6.0},
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'day': date(2022, 1, 1), 'duration': 6.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'day': date(2022, 1, 1), 'duration': 6.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'day': date(2022, 3, 1), 'duration': 3.0},
        ]
        employee = EmployeeFactory()
        event_instance = EmployeeEvents(employee, events)

        events_per_day = event_instance.group_events_per_project()

        assert len(events_per_day) == 2

        assert events_per_day[1].days_spent == 2
        assert events_per_day[1].events == [
            {'project_id': 1, 'employee': employee.name, 'date': date(2022, 1, 1), 'duration': 12.0,
             'days_spent': 2.0}]
        assert events_per_day[1].total_duration == 12.0

        assert events_per_day[2].days_spent == 1.5
        assert events_per_day[2].events == [
            {'project_id': 2, 'employee': employee.name, 'date': date(2022, 1, 1), 'duration': 6.0,
             'days_spent': 1.0},
            {'project_id': 2, 'employee': employee.name, 'date': date(2022, 3, 1), 'duration': 3.0,
             'days_spent': 0.5}]
        assert events_per_day[2].total_duration == 9.0


@pytest.mark.django_db
def test_count_number_days_spent_per_project():
    # Create mock data
    employee = EmployeeFactory()
    event = Event(project_id=1, name="Test Project", subproject_name=None, day=date.today(), duration=8.0)
    event_2 = Event(project_id=1, name="Test Project", subproject_name=None, day=date.today(), duration=8.0)
    events = [event, event_2]

    # Call the function with the mock data
    result = count_number_days_spent_per_project(events, employee)

    # Assert that the output is as expected
    assert len(result) == 1
    assert event["project_id"] in result
    assert result[event["project_id"]]['days_spent'] == 2
    assert result[event["project_id"]]['duration'] == 16
