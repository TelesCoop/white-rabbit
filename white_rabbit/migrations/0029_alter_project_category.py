# Generated by Django 3.2.10 on 2024-04-30 09:35

from django.db import migrations, models
import white_rabbit.models


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0028_project_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='category',
            field=models.CharField(blank=True, choices=[(white_rabbit.models.ProjectCategories['PRO_BONO'], 'Pro-bono'), (white_rabbit.models.ProjectCategories['CLIENT'], 'Client'), (white_rabbit.models.ProjectCategories['INTERNAL'], 'Interne'), (white_rabbit.models.ProjectCategories['ROLE'], 'Rôle'), (white_rabbit.models.ProjectCategories['OTHER'], 'Autre')], max_length=12),
        ),
    ]
