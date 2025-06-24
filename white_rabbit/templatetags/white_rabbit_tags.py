import datetime
import json
import numbers
import locale

from django.template.defaultfilters import pluralize, floatformat
from django.template.defaulttags import register

from white_rabbit.constants import SEVERITY_COLORS
from white_rabbit.models import PROJECT_CATEGORY_TO_DISPLAY_NAME, Category
from white_rabbit.utils import is_total_key


@register.simple_tag
def project_name(project_details, project_id):
    return project_details[project_id]["name"]


@register.simple_tag
def subproject_total(employee_events, employee_name, project_id, subproject_name):
    to_return = (
        employee_events[employee_name]
        .get(project_id, {})
        .get("subprojects", {})
        .get(subproject_name, {})
        .get("duration", "")
    )
    if to_return:
        to_return = floatformat(to_return, 1)
    return to_return


@register.simple_tag
def iterate_json(json_string):
    return json.loads(json_string).items()


@register.filter
def json_loads(value):
    """It returns variable type as a pure string name"""
    return json.loads(value)


@register.filter
def get_type(value):
    """It returns variable type as a pure string name"""
    return type(value).__name__


@register.filter
def find_project(project_id, projects):
    return projects.get(project_id, None)


@register.filter
def format_datetime_to_hour(project_datetime):
    if datetime is None or isinstance(project_datetime, datetime.date):
        return ""
    return project_datetime.strftime("%H:%M")


@register.filter
def find_project_name(project_id, projects):
    project = find_project(project_id, projects)
    if project is None:
        return "Inconnu"
    return project.get("name", "Non attribué")


@register.filter
def find_project_category(project_id, projects):
    project = find_project(project_id, projects)
    if project is None:
        return ""
    return project.get("category", "")


@register.filter
def find_category_color(category_name, company):
    try:
        category = company.categories.get(name=category_name)
        return category.color
    except Category.DoesNotExist:
        return "bg-white-100"


@register.filter
def get_category_display_name(category: str):
    return PROJECT_CATEGORY_TO_DISPLAY_NAME.get(category, "Non défini")


@register.simple_tag
def filter_by_project_id_and_month(events, project_id, month):
    month_data = events.get(month)
    if month_data:
        project_data = month_data.get("projects")
        if project_data:
            project = project_data.get(project_id, None)
            if project:
                return project.total_duration
    return ""


@register.filter
def get_employee_events(employees_events, employee_name):
    return employees_events.get(employee_name, "")


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def currency(value):
    locale.setlocale(locale.LC_MONETARY, "fr_FR.UTF-8")
    # Remove cents from the financial values
    locale._override_localeconv = {"frac_digits": 0}
    return locale.currency(value, symbol=True, grouping=True)


@register.filter
def format_date(date):
    if is_total_key(date):
        return date
    # Convert the string to a datetime object
    date_object = datetime.datetime.strptime(date, "%m-%Y")

    # Format the datetime object into a readable date
    readable_date = date_object.strftime("%b %Y")

    return readable_date


@register.filter
def convert_duration_based_on_periodicity(duration, periodicity):
    return f"{round(duration, 2)} jour{pluralize(duration)} "


@register.simple_tag
def get_projects(projects_events_by_ids, projects_details, periodicity):
    projects = []
    for project_id in projects_events_by_ids:
        project = find_project(project_id, projects_details)
        if project is None or project.get("name") is None:
            continue
        duration = projects_events_by_ids[project_id]["days_spent"]

        if duration is not None and isinstance(duration, numbers.Number):
            duration = convert_duration_based_on_periodicity(duration, periodicity)
        projects.append((project["name"], duration))

    return projects


@register.simple_tag
def get_projects_str(projects_events_by_ids, projects_details, periodicity):
    projects = get_projects(projects_events_by_ids, projects_details, periodicity)

    return projects


@register.filter
def week_color(value):
    SUCCESS_COLOR = SEVERITY_COLORS[-1]
    WEEK_THRESHOLDS = [1, 2, 3, 4, 5]

    if value is None or not isinstance(value, (int, float)):
        return ""

    for index, color in enumerate(SEVERITY_COLORS):
        if value < WEEK_THRESHOLDS[index]:
            return color
    return SUCCESS_COLOR


def number_of_working_days_for_period_key(period_key: str):
    # period_key is MM-YYYY
    month, year = period_key.split("-")
    month = int(month)
    year = int(year)
    n_days = 0
    for day in range(1, 32):
        try:
            date = datetime.datetime(year, month, day)
            if date.weekday() < 5:
                n_days += 1
        except ValueError:
            continue
    return n_days


@register.filter
def monthly_hours_color(hours, period_key):
    """
    Return the color corresponding to the number of hours worked in a month,
    taking into account the number of expecte hours for that month, based on the number
    of working days.
    Could be improved by taking into account the number of working days / hours for each
    employee.
    """
    SUCCESS_COLOR = SEVERITY_COLORS[-1]
    n_days = number_of_working_days_for_period_key(period_key)
    THRESHOLDS = [12 * n_days, 10 * n_days, 8 * n_days, 7 * n_days, 6 * n_days]

    if hours is None or not isinstance(hours, (int, float)):
        return ""

    for index, color in enumerate(SEVERITY_COLORS):
        if hours >= THRESHOLDS[index]:
            return color
    return SUCCESS_COLOR


@register.filter
def employee_events_to_tooltip(employee_events):
    days_spent = []
    for project in employee_events["events"]:
        days_spent.append(
            f"{floatformat(project['days_spent'], 2)} jour{pluralize(project['days_spent'])} le {project['start_datetime']} \n"
        )
    return days_spent


@register.filter
def get_event_by_date(events, date):
    return events.get(date, None)


@register.filter
def get_events_by_category(events, category):
    return events.get(category, "")


@register.filter
def dict_items(dictionary):
    return dictionary.items()
