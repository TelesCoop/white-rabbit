# Generated by Django 3.2.10 on 2024-04-30 09:57

from django.db import migrations, models
import white_rabbit.models


class Migration(migrations.Migration):
    dependencies = [
        ('white_rabbit', '0022_alter_employee_calendar_ical_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='disabled',
            field=models.BooleanField(default=False, help_text='Salarié désactivé', verbose_name='désactivé'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_1',
            field=models.BooleanField(default=True, verbose_name='travaille le lundi'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_2',
            field=models.BooleanField(default=True, verbose_name='travaille le mardi'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_3',
            field=models.BooleanField(default=True, verbose_name='travaille le mercredi'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_4',
            field=models.BooleanField(default=True, verbose_name='travaille le jeudi'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_5',
            field=models.BooleanField(default=True, verbose_name='travaille le vendredi'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_6',
            field=models.BooleanField(default=False, verbose_name='travaille le samedi'),
        ),
        migrations.AddField(
            model_name='employee',
            name='works_day_7',
            field=models.BooleanField(default=False, verbose_name='travaille le dimanche'),
        ),
        migrations.AddField(
            model_name='project',
            name='category',
            field=models.CharField(blank=True,
                                   choices=[(white_rabbit.models.ProjectCategories['PRO_BONO'].value, 'Pro-bono'),
                                            (white_rabbit.models.ProjectCategories['CLIENT'].value, 'Client'),
                                            (white_rabbit.models.ProjectCategories['INTERNAL'].value, 'Interne'),
                                            (white_rabbit.models.ProjectCategories['ROLE'].value, 'Rôle'),
                                            (white_rabbit.models.ProjectCategories['OTHER'].value, 'Autre')],
                                   max_length=12),
        ),
        migrations.AddField(
            model_name='project',
            name='end_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='start_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name='project',
            name='is_client_project',
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together={('lowercase_name', 'name', 'company', 'category', "start_datetime", "end_datetime")},
        ),

    ]
