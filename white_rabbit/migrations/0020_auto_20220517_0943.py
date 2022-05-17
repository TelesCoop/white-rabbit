# Generated by Django 3.2.10 on 2022-05-17 07:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('white_rabbit', '0019_auto_20211118_1354'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='days_sold',
            field=models.IntegerField(default=0, help_text="Il s'agit du nombre de jours vendu pour ce projet", verbose_name='Jours vendu'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='employees', to='white_rabbit.company', verbose_name='entreprise'),
        ),
    ]