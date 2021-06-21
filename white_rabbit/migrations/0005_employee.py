# Generated by Django 3.1.7 on 2021-06-18 08:16

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('white_rabbit', '0004_auto_20210618_0815'),
    ]

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateField(auto_now=True)),
                ('calendar_ical_url', models.CharField(max_length=150, verbose_name='URL calendrier Google')),
                ('availability_per_day', models.IntegerField(default=8, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(24)], verbose_name='heure travaillées par jour')),
                ('company', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='white_rabbit.company')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'salarié',
            },
        ),
    ]
