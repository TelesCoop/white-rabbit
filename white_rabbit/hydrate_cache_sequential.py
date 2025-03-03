import time

import requests
import datetime
from django.core.cache import cache

from white_rabbit.events import read_events
from white_rabbit.models import Employee
from white_rabbit.settings import DEFAULT_CACHE_DURATION


def hydrate_cache_sequential():
    employees = Employee.objects.filter(
        start_time_tracking_from__isnull=False,
        start_time_tracking_from__lte=datetime.date.today(),
    )
    urls = [employee.calendar_ical_url for employee in employees]
    start = time.time()
    responses = [requests.get(u) for u in urls]
    print(
        f"Fetching data from online icals for {len(employees)} employees took {time.time() - start:.2f} seconds."
    )
    start = time.time()
    for response, employee in zip(responses, employees):
        if response:
            data = response.content.decode()
            events = read_events(data, employee)
            cache.set(str(employee.id), events, DEFAULT_CACHE_DURATION)
    print(
        f"Processing events and saving in cache for {len(employees)} employees took {time.time() - start:.2f} seconds."
    )
