from unittest.mock import ANY
import pytest
from datetime import date
from white_rabbit.events import process_employees_events, Event, EventsPerEmployee, \
    MonthDetailPerEmployeePerMonth
from white_rabbit.tests.factory import EmployeeFactory


@pytest.mark.django_db
def test_process_employees_events():
    employee = EmployeeFactory()
    project_id = 1
    project_id_2 = 2
    event = Event(project_id=project_id, name="Project", subproject_name=None, day=date.today(), duration=8.0)
    event_2 = Event(project_id=project_id_2, name="Project 02", subproject_name=None, day=date(2024, 1, 1),
                    duration=6.0)
    event_3 = Event(project_id=project_id, name="Project 03", subproject_name=None, day=date(2024, 1, 1),
                    duration=8.0)
    events_per_employee: EventsPerEmployee = {employee: [event, event_2, event_3]}

    employees_data: MonthDetailPerEmployeePerMonth = process_employees_events(events_per_employee)

    assert len(employees_data) == 1
    assert employee.name in employees_data
    assert employees_data[employee.name].events == [
        {'project_id': 1, 'name': 'Project', 'subproject_name': None, 'day': ANY,
         'duration': 8.0},
        {'project_id': 2, 'name': 'Project 02', 'subproject_name': None, 'day': ANY,
         'duration': 6.0},
        {'project_id': 1, 'name': 'Project 03', 'subproject_name': None, 'day': ANY,
         'duration': 8.0}
    ]
    assert employees_data[employee.name].projects[project_id].days_spent == 2
    assert employees_data[employee.name].projects[project_id_2].days_spent == 1
    assert employees_data[employee.name].projects[project_id].total_duration == 16.0
    assert employees_data[employee.name].projects[project_id_2].total_duration == 6.0
