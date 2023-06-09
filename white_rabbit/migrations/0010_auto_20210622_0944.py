# Generated by Django 3.2.4 on 2021-06-22 09:44

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0009_alter_employee_calendar_ical_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='company',
            name='default_day_working_hours',
        ),
        migrations.RemoveField(
            model_name='company',
            name='min_working_hours_for_full_day',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='availability_per_day',
        ),
        migrations.AddField(
            model_name='employee',
            name='default_day_working_hours',
            field=models.IntegerField(default=8, help_text="Pour une journée incomplète, ce total est utilisé pour calculer la proportion d'une journée passée sur un projet", validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(24)], verbose_name='heures travaillées par jour'),
        ),
        migrations.AddField(
            model_name='employee',
            name='min_working_hours_for_full_day',
            field=models.DecimalField(decimal_places=1, default=6, help_text="Nombre d'heures de travail à partir au-delà duquel on considère une journée complète", max_digits=3, verbose_name='nb heures journée complète'),
        ),
    ]
