import datetime
from typing import List, Tuple

import html2text
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from white_rabbit.constants import DayState
from white_rabbit.events import get_events_by_url
from white_rabbit.models import Employee
from white_rabbit.state_of_day import state_of_days_for_week

FIRST_DAY = datetime.date(2021, 4, 5)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for employee in Employee.objects.all():
            if not employee.user.email:
                continue

            events = get_events_by_url(employee.calendar_ical_url)

            missing_days: List[Tuple] = []
            day = employee.start_time_tracking_from
            today = datetime.date.today()
            end_of_last_week = (
                today
                + datetime.timedelta(days=6 - today.weekday())
                - datetime.timedelta(days=7)
            )
            last_day = end_of_last_week
            if employee.end_time_tracking_on:
                last_day = min(end_of_last_week, employee.end_time_tracking_on)

            while day < last_day:
                for day, state_of_day in state_of_days_for_week(
                    events, employee, day=day
                ).items():
                    if state_of_day["state"] != DayState.complete:
                        missing_days.append((day, state_of_day))
                day += datetime.timedelta(days=7)

            if not missing_days:
                # all days are complete
                continue

            # send emails
            html_message = render_to_string(
                "email/missing_days_reminder.html", {"days": missing_days}
            )
            message = html2text.html2text(html_message)
            send_mail(
                "[Lapin Blanc]: Des jours manquants à remplir",
                message,
                "contact@telescoop.fr",
                [employee.user.email],
                html_message=html_message,
            )
