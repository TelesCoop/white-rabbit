# Generated by Django 3.2.10 on 2023-02-24 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0022_alter_employee_calendar_ical_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together={('lowercase_name', 'company', 'start_date')},
        ),
    ]
