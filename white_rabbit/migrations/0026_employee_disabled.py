# Generated by Django 3.2.10 on 2024-04-08 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0025_project_is_pro_bono_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='disabled',
            field=models.BooleanField(default=False, help_text='Salarié désactivé', verbose_name='désactivé'),
        ),
    ]
