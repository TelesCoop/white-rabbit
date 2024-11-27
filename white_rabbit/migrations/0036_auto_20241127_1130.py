# Generated by Django 5.0.6 on 2024-11-27 11:30

from django.db import migrations


def save_all_projects_and_aliases(apps, schema_editor):
    # so that lowercase_name is updated
    Project = apps.get_model("white_rabbit", "Project")
    Alias = apps.get_model("white_rabbit", "Alias")
    for project in Project.objects.all():
        project.save()
    for alias in Alias.objects.all():
        alias.save()


class Migration(migrations.Migration):

    dependencies = [
        ("white_rabbit", "0035_alter_project_unique_together_project_project_name"),
    ]

    operations = [
        migrations.RunPython(save_all_projects_and_aliases, reverse_code=migrations.RunPython.noop)
    ]
