import time
from collections import defaultdict

import grequests
import datetime
from django.core.cache import cache

from white_rabbit.events import read_events
from white_rabbit.models import Employee, Project
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.settings import DEFAULT_CACHE_DURATION


def hydrate_cache():
    employees = Employee.objects.filter(
        start_time_tracking_from__isnull=False,
        start_time_tracking_from__lte=datetime.date.today(),
    )
    urls = [employee.calendar_ical_url for employee in employees]
    start = time.time()
    rs = (grequests.get(u) for u in urls)
    responses = grequests.map(rs)
    print(
        f"Fetching data from online icals for {len(employees)} employees took {time.time() - start:.2f} seconds."
    )
    project_finder = ProjectFinder()
    start = time.time()
    subprojects_per_project = defaultdict(set)
    for response, employee in zip(responses, employees):
        if response:
            data = response.content.decode()
            try:
                events = read_events(data, employee, project_finder=project_finder)
            except Exception as e:
                print(f"Error processing calendar for employee {employee.id} ({employee.user.email}): {e}")
                continue
            for event in events:
                if event["subproject_name"] and event["project_id"]:
                    subprojects_per_project[event["project_id"]].add(event["subproject_name"])
            cache.set(str(employee.id), events, DEFAULT_CACHE_DURATION)
    projects = Project.objects.filter(pk__in=subprojects_per_project.keys())
    for project in projects:
        project.subproject_names = sorted(subprojects_per_project[project.pk])
    Project.objects.bulk_update(projects, ["subproject_names"])
    print(
        f"Processing events and saving in cache for {len(employees)} employees took {time.time() - start:.2f} seconds."
    )
