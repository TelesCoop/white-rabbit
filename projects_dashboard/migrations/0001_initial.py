# Generated by Django 3.1.7 on 2021-03-11 20:12

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('calendar_ical_url', models.CharField(max_length=150)),
                ('availability_per_day', models.IntegerField(default=8, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(24)])),
            ],
        ),
    ]
