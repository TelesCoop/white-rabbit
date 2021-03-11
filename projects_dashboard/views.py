from itertools import groupby
from datetime import date, timedelta
from django.shortcuts import render
from django.views import View
from .events import read_events
import requests


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


class HomeView(View):
    def get(self, request):
        # <view logic>
        url = "https://calendar.google.com/calendar/ical/0rn9t0elkuafqm6401rossmd8g%40group.calendar.google.com/public/basic.ics"
        r = requests.get(url)
        data = r.content.decode()
        events = read_events(data)
        result = {
            "time_per_project": time_per_project(events),
            "state_of_days": state_of_days(
                events, date(2021, 3, 15), date(2021, 3, 19)
            ),
        }

        return render(request, "home.html", {"events": events, "result": result})
