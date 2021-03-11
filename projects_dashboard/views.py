from itertools import groupby
from datetime import date, timedelta

from django.shortcuts import render
from django.views import View
from .events import get_events_by_url
from jours_feries_france import JoursFeries


def state_of_days(events: list, start_date: date, end_date):
    result = {}
    delta = end_date - start_date
    events_per_day = {k: list(g) for k, g in groupby(events, lambda x: x["day"])}

    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)

        result[day] = {
            "total_duration": sum(
                event["duration"] for event in events_per_day.get(day, [])
            ),
            "projects": {},
        }

        for event in events_per_day.get(day, []):
            if event["name"] not in result[day]["projects"]:
                result[day]["projects"][event["name"]] = {
                    "name": event["name"],
                    "total_duration": 0,
                    "part_time": 0,
                }
            result[day]["projects"][event["name"]]["total_duration"] += event[
                "duration"
            ]
            result[day]["projects"][event["name"]]["part_time"] = (
                result[day]["projects"][event["name"]]["total_duration"]
                / result[day]["total_duration"]
            )

    return result


def time_per_project(events: list):
    result = {}

    for event in events:
        if event["name"] not in result:
            result[event["name"]] = 0
        result[event["name"]] += event["duration"]

    return result


def available_time_of_employee(employee, start_date: date, end_date: date):
    events = get_events_by_url(employee.calendar_ical_url)
    events_per_day = {k: list(g) for k, g in groupby(events, lambda x: x["day"])}
    delta = end_date - start_date
    availability_duration = 0

    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        # for weekend and bank holiday
        if day.weekday() >= 5 or JoursFeries.is_bank_holiday(day, zone="Métropole"):
            continue

        busy_duration = sum(event["duration"] for event in events_per_day.get(day, []))
        availability_duration += max(employee.availability_per_day - busy_duration, 0)

    return availability_duration


class HomeView(View):
    def get(self, request):
        # <view logic>
        url = "https://calendar.google.com/calendar/ical/0rn9t0elkuafqm6401rossmd8g%40group.calendar.google.com/public/basic.ics"
        events = get_events_by_url(url)
        result = {
            "time_per_project": time_per_project(events),
            "state_of_days": state_of_days(
                events, date(2021, 3, 15), date(2021, 3, 19)
            ),
        }

        return render(request, "home.html", {"events": events, "result": result})
