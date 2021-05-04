import datetime
from collections import defaultdict
from typing import List, DefaultDict, Tuple

import html2text
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from white_rabbit.constants import DayState
from white_rabbit.events import get_all_events_per_employee
from white_rabbit.models import Employee
from white_rabbit.state_of_day import state_of_days_per_employee_for_week

FIRST_DAY = datetime.date(2021, 4, 5)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # gather missing days since beginning of April 2021 per employee
        events_per_employee = get_all_events_per_employee()
        missing_days_per_employee: DefaultDict[Employee, List[Tuple]] = defaultdict(
            lambda: []
        )
        day = FIRST_DAY
        end_of_current_week = datetime.date.today() - datetime.timedelta(
            days=day.weekday() + 6
        )
        while day < end_of_current_week:
            for day, data in state_of_days_per_employee_for_week(
                events_per_employee, day=day
            ).items():
                for employee, state_of_day in data.items():
                    if state_of_day["state"] != DayState.complete:
                        missing_days_per_employee[employee].append((day, state_of_day))
            day += datetime.timedelta(days=7)

        # send emails
        for employee, missing_days in missing_days_per_employee.items():
            if not missing_days:
                # all days are complete
                continue
            html_message = render_to_string(
                "email/missing_days_reminder.html", {"days": missing_days}
            )
            message = html2text.html2text(html_message)
            send_mail(
                "[Lapin Blanc]: Des jours manquants à remplir",
                message,
                "contact@telescoop.fr",
                [employee.email],
                html_message=html_message,
            )
