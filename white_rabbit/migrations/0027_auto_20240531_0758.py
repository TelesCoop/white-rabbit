# Generated by Django 3.2.10 on 2024-05-31 07:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0026_auto_20240515_1002'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='days_sold',
            new_name="estimated_days_count"
        ),
    ]
