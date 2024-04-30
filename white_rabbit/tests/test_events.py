import pytest
from datetime import date, datetime
from white_rabbit.events import EmployeeEvents
from white_rabbit.models import ProjectCategories
from white_rabbit.tests.factory import EmployeeFactory


class TestEmployeeEvents:
    @pytest.fixture
    def event_instance(self, db):
        employee = EmployeeFactory()
        events = [
            {
                'project_id': 1, 'name': 'Project', 'subproject_name': None, 'start_datetime': datetime(2022, 1, 1),
                "category": ProjectCategories.PRO_BONO.value, 'duration': 2.0
            },
            {
                'project_id': 2, 'name': 'Project_2', 'subproject_name': None, 'start_datetime': datetime(2022, 1, 2),
                'duration': 3.0, "category": ProjectCategories.PRO_BONO.value
            },
            {
                'project_id': 3, 'name': 'Project_3', 'subproject_name': None, 'start_datetime': datetime(2022, 1, 1),
                "category": ProjectCategories.CLIENT.value,
                'duration': 1.0
            },
            {
                'project_id': 4, 'name': 'Project_4', 'subproject_name': None, 'start_datetime': datetime(2022, 3, 1),
                "category": ProjectCategories.CLIENT.value,
                'duration': 1.0
            },
        ]
        return EmployeeEvents(employee, events)

    def test_group_events_per_project_category(self, event_instance):
        result = event_instance.group_events_per_project_category(month=1)

        assert ProjectCategories.CLIENT.value in result
        assert ProjectCategories.PRO_BONO.value in result

        assert len(result[ProjectCategories.PRO_BONO.value]["events"]) == 2

    def test_filter_events_per_month(self, event_instance):
        date_to_find = date(2022, 1, 1)
        events_per_month = event_instance.filter_events_per_month(date_to_find)
        assert len(events_per_month[date_to_find]) == 3

    def test_group_events_per_project(self, event_instance):
        events = [
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'start_datetime': datetime(2022, 1, 1),
             'duration': 6.0},
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None, 'start_datetime': datetime(2022, 1, 1),
             'duration': 6.0},
            {'project_id': 3, 'name': 'Project2', 'subproject_name': None, 'start_datetime': datetime(2022, 1, 1),
             'duration': 6.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None, 'start_datetime': datetime(2022, 3, 1),
             'duration': 3.0},
        ]
        employee = EmployeeFactory()
        event_instance = EmployeeEvents(employee, events)

        events_per_day = event_instance.group_events_per_project()

        assert len(events_per_day) == 3
        assert events_per_day == {
            1: {'days_spent': 2.0, 'duration': 12.0, 'category': '', 'events': [
                {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
                 'start_datetime': datetime(2022, 1, 1, 0, 0), 'duration': 6.0},
                {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
                 'start_datetime': datetime(2022, 1, 1, 0, 0), 'duration': 6.0}]},
            3: {'days_spent': 1.0, 'duration': 6.0, 'category': '', 'events': [
                {'project_id': 3, 'name': 'Project2', 'subproject_name': None,
                 'start_datetime': datetime(2022, 1, 1, 0, 0), 'duration': 6.0}]},
            2: {'days_spent': 0.5, 'duration': 3.0, 'category': '', 'events': [
                {'project_id': 2, 'name': 'Project2', 'subproject_name': None,
                 'start_datetime': datetime(2022, 3, 1, 0, 0), 'duration': 3.0}
            ]}
        }

    def test_total_project_per_time_period(self, db):
        current_year = datetime.now().year
        current_month = datetime.now().month
        events = [
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
             'start_datetime': datetime(current_year, current_month, 2),
             'duration': 6.0},
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
             'start_datetime': datetime(current_year, current_month, 2),
             'duration': 6.0},
            {'project_id': 3, 'name': 'Project2', 'subproject_name': None,
             'start_datetime': datetime(current_year, current_month, 2),
             'duration': 6.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None,
             'start_datetime': datetime(current_year, max(current_month + 1, 12), 1),
             'duration': 3.0},
        ]
        employee = EmployeeFactory()
        event_instance = EmployeeEvents(employee, events)

        total_project_per_time_period = event_instance.total_project_per_time_period(time_period="month", n_periods=2)

        assert total_project_per_time_period == {
            '5-2024':
                {
                    'availability': 18.0,
                    'projects': {
                        1: {'days_spent': 2.0, 'duration': 12.0, 'category': '', 'events': [
                            {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
                             'start_datetime': datetime(2024, 5, 2, 0, 0), 'duration': 6.0},
                            {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
                             'start_datetime': datetime(2024, 5, 2, 0, 0), 'duration': 6.0}]},
                        3: {'days_spent': 1.0, 'duration': 6.0, 'category': '', 'events': [
                            {'project_id': 3, 'name': 'Project2', 'subproject_name': None,
                             'start_datetime': datetime(2024, 5, 2, 0, 0), 'duration': 6.0}]}}},
            '4-2024': {'availability': 21.0, 'projects': {}}}

    def test_upcoming_events(self, db):
        employee = EmployeeFactory()
        events = [
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
             'start_datetime': datetime(2022, 1, 2),
             'duration': 6.0},
            {'project_id': 1, 'name': 'Project1', 'subproject_name': None,
             'start_datetime': datetime(2022, 1, 2),
             'duration': 6.0},
            {'project_id': 3, 'name': 'Project2', 'subproject_name': None,
             'start_datetime': datetime(2022, 1, 2),
             'duration': 6.0},
            {'project_id': 2, 'name': 'Project2', 'subproject_name': None,
             'start_datetime': datetime(2022, 3, 1),
             'duration': 3.0},
        ]
        event_instance = EmployeeEvents(employee, events)
