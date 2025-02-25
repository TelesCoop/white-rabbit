import datetime
from typing import List, Tuple

import html2text
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from white_rabbit.constants import DayState
from white_rabbit.events import get_events_by_url
from white_rabbit.models import Employee
from white_rabbit.project_name_finder import ProjectFinder
from white_rabbit.settings import ENVIRONMENT
from white_rabbit.state_of_day import state_of_days_for_week


def send_missing_days_email(missing_days: List[Tuple], employee: Employee):
    html_message = render_to_string(
        "email/missing_days_reminder.html",
        {"days": missing_days, "current_year": datetime.date.today().year},
    )
    message = html2text.html2text(html_message)
    send_mail(
        "[Lapin Blanc]: Des jours manquants à remplir",
        message,
        "contact@telescoop.fr",
        [employee.user.email],
        html_message=html_message,
    )


class Command(BaseCommand):
    def handle(self, *args, **options):
        project_finder = ProjectFinder()
        for employee in Employee.objects.filter(
            user__email__isnull=False,
            start_time_tracking_from__isnull=False,
        ):
            try:
                events = get_events_by_url(
                    employee.calendar_ical_url, employee, project_finder
                )
            except ValueError:
                print(f"could not get events for {employee.user.email}")
                continue

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
                for day_in_week, state_of_day in state_of_days_for_week(
                    events, employee, day=day
                ).items():
                    if not getattr(employee, f"works_day_{day_in_week.weekday() + 1}"):
                        # employee does not work on that day, so no reminders to be sent
                        continue
                    if day_in_week < employee.start_time_tracking_from:
                        # can happen in the first week
                        continue

                    if state_of_day["state"] != DayState.complete:
                        missing_days.append((day_in_week, state_of_day))
                day += datetime.timedelta(days=7)

            if not missing_days:
                # all days are complete
                continue

            if ENVIRONMENT != "production":
                print(f"missing days for {employee.user.email}: {missing_days}")
                continue

            send_missing_days_email(missing_days, employee)
