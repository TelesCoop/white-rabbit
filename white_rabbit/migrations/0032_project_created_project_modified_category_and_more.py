# Generated by Django 5.0.6 on 2024-11-26 18:12
from enum import Enum

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class ProjectCategories(Enum):
    PRO_BONO = "PRO_BONO"
    CLIENT = "CLIENT"
    INTERNAL = "INTERNAL"
    ROLE = "ROLE"
    OTHER = "OTHER"
    OFF_WORK = "OFF_WORK"
    OKLM = "OKLM"
    SALES = "SALES"
    FORMATION = "FORMATION"


PROJECT_CATEGORY_TO_DISPLAY_NAME = {
    ProjectCategories.PRO_BONO.value: "Pro-bono",
    ProjectCategories.CLIENT.value: "Client",
    ProjectCategories.INTERNAL.value: "Interne",
    ProjectCategories.ROLE.value: "Rôle",
    ProjectCategories.OTHER.value: "Autre",
    ProjectCategories.OFF_WORK.value: "Congé",
    ProjectCategories.OKLM.value: "Oklm",
    ProjectCategories.SALES.value: "Commercial",
    ProjectCategories.FORMATION.value: "Formation",
    "": "Non défini",
}


def fill_category_instance(apps, schema_editor):
    Project = apps.get_model("white_rabbit", "Project")
    Category = apps.get_model("white_rabbit", "Category")
    for project in Project.objects.all():
        category, _ = Category.objects.get_or_create(
            name=PROJECT_CATEGORY_TO_DISPLAY_NAME[project.category],
            company=project.company,
        )
        project.category_instance = category
        project.save()


class Migration(migrations.Migration):

    dependencies = [
        ("white_rabbit", "0031_alter_project_category_alter_project_total_sold"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="modified",
            field=models.DateField(auto_now=True),
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateField(auto_now=True)),
                ("name", models.CharField(max_length=32, verbose_name="nom")),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="categories",
                        to="white_rabbit.company",
                        verbose_name="entreprise",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="project",
            name="category_instance",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="projects",
                to="white_rabbit.category",
                verbose_name="catégorie",
            ),
        ),
        migrations.RunPython(fill_category_instance, migrations.RunPython.noop),
        # migrations.RemoveField(model_name="project", name="category"),
    ]
