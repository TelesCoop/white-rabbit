import json
import numbers

from django.template.defaulttags import register

from white_rabbit.constants import DEFAULT_ROUND_DURATION_PRECISION, DEFAULT_DAY_WORKING_HOURS
from white_rabbit.utils import convert_duration_to_work_hours_and_minutes, convert_duration_to_work_day


@register.simple_tag
def project_name(project_details, project_id):
    return project_details[project_id]["name"]


@register.simple_tag
def iterate_json(json_string):
    return json.loads(json_string).items()


@register.filter
def json_loads(value):
    """ It returns variable type as a pure string name """
    return json.loads(value)


@register.filter
def get_type(value):
    """ It returns variable type as a pure string name """
    return type(value).__name__


@register.filter
def find_project(project_id, projects):
    project = projects.get(int(project_id), None)
    if project is None:
        return None
    return project


@register.filter
def find_project_name(project_id, projects):
    return find_project(project_id, projects).get("name", None)


@register.filter
def convert_duration_based_on_periodicity(duration, periodicity):
    if periodicity == "week":
        return convert_duration_to_work_hours_and_minutes(duration)
    return convert_duration_to_work_day(duration)


@register.simple_tag
def get_projects(projects_events_by_ids, projects_details, periodicity):
    projects = []
    for project_id in projects_events_by_ids:
        project = find_project(project_id, projects_details)
        if project is None or project.get("name") is None:
            continue
        duration = projects_events_by_ids[project_id].total_duration
        # breakpoint()
        # if duration is not None and isinstance(duration, numbers.Number):
        #     duration = convert_duration_based_on_periodicity(duration, periodicity)
        projects.append(f"{project["name"]} {duration}")
    return projects


@register.simple_tag
def get_projects_str(projects_events_by_ids, projects_details, periodicity):
    projects = get_projects(projects_events_by_ids, projects_details, periodicity)
    return ", ".join(projects)


@register.filter
def week_color(value):
    COLORS = ["#EEA6A6;", "#eec3a6;", "#eedaa6;", "#eceea6;", "#c2eea6;"]
    SUCCESS_COLOR = COLORS[-1]
    WEEK_THRESHOLDS = [1, 2, 3, 4, 5]

    if value is None or not isinstance(value, (int, float)):
        return ""

    for index, color in enumerate(COLORS):
        if value < WEEK_THRESHOLDS[index]:
            return color
    return SUCCESS_COLOR
