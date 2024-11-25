# Generated by Django 5.0.6 on 2024-11-25 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("white_rabbit", "0030_merge_20241115_1157"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PRO_BONO", "Pro-bono"),
                    ("CLIENT", "Client"),
                    ("INTERNAL", "Interne"),
                    ("ROLE", "Rôle"),
                    ("OTHER", "Autre"),
                    ("OFF_WORK", "Congé"),
                    ("OKLM", "Oklm"),
                    ("SALES", "Commercial"),
                    ("FORMATION", "Formation"),
                    ("", "Non défini"),
                ],
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="total_sold",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Montant total vendu pour le projet en € (hors coûts refacturés)",
                max_digits=10,
                verbose_name="Prix total de vente (€ HT)",
            ),
        ),
    ]
