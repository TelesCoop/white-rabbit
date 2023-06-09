# Generated by Django 3.2.4 on 2021-11-17 08:54

from django.db import migrations, models


def set_lowercase_name(apps, _):
    Alias = apps.get_model("white_rabbit", "Alias")
    Project = apps.get_model("white_rabbit", "Project")
    for alias in Alias.objects.all():
        alias.lowercase_name = alias.name.lower()
        alias.save()
    for project in Project.objects.all():
        project.lowercase_name = project.name.lower()
        project.save()


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0016_auto_20211117_0844'),
    ]

    operations = [
        migrations.AddField(
            model_name='alias',
            name='lowercase_name',
            field=models.CharField(max_length=32, null=True, verbose_name='nom en minuscule'),
        ),
        migrations.AddField(
            model_name='project',
            name='lowercase_name',
            field=models.CharField(max_length=32, null=True, verbose_name='nom en minuscule'),
        ),
        migrations.RunPython(set_lowercase_name, lambda _, _2: None)
    ]
