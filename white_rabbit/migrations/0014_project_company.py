# Generated by Django 3.2.4 on 2021-11-16 10:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0013_auto_20211109_1623'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='white_rabbit.company', verbose_name='entreprise'),
            preserve_default=False,
        ),
    ]