# Generated by Django 3.1.7 on 2021-03-28 11:58

from django.db import migrations
from django.db.migrations import RunPython

EMPLOYEES = [
    # 3, 4, 5
    ("Maxime", "https://calendar.google.com/calendar/ical/0rn9t0elkuafqm6401rossmd8g%40group.calendar.google.com/public/basic.ics"),
    ("Antoine", "https://calendar.google.com/calendar/ical/aecj13q1d2q7nu34lflrb7ssc0%40group.calendar.google.com/public/basic.ics"),
    ("Quentin", "https://calendar.google.com/calendar/ical/62kd60uah4s7cbs6j1qoobc3f0%40group.calendar.google.com/public/basic.ics"),
]


def add_employees(apps, schema_editor):
    Employee = apps.get_model("white_rabbit", "Employee")
    for name, url in EMPLOYEES:
        Employee.objects.create(name=name, calendar_ical_url=url, email=f"{name.lower()}@telescoop.fr")

def undo_add_employees(apps, schema_editor):
    Employee = apps.get_model("white_rabbit", "Employee")
    for name, _ in EMPLOYEES:
        Employee.objects.get(name=name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0002_auto_20210328_1157'),
    ]

    operations = [
        RunPython(add_employees, undo_add_employees)
    ]
