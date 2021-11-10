# Generated by Django 3.2.4 on 2021-07-19 10:50

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0010_auto_20210622_0944'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='start_time_tracking_from',
            field=models.DateField(blank=True, default=datetime.datetime.now, help_text='Pour désactiver le suivi du temps, laisser ce champ vide', null=True, verbose_name='Début du suivi de temps'),
        ),
    ]