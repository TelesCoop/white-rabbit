# Generated by Django 5.0.12 on 2025-02-16 09:11

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("white_rabbit", "0040_alter_invoice_comment_alter_invoice_number"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="invoice",
            options={"verbose_name": "facture/devis"},
        ),
        migrations.AddField(
            model_name="employee",
            name="is_paid_hourly",
            field=models.BooleanField(
                default=False,
                help_text="si coché, le calcul des jours est au pro-rata d'une journée de travail complète, donc un jour de travail peut être compté comme moins d'un jour, voire plusieurs jours",
                verbose_name="forfait heure",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="default_day_working_hours",
            field=models.IntegerField(
                default=8,
                help_text="En forfait jour, pour une journée incomplète, ce total est utilisé pour calculer la proportion d'une journée passée sur un projet. En forfait heures, c'est le nombre d'heures travaillées par jour.",
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(24),
                ],
                verbose_name="heures travaillées par jour",
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="amount",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Montant facture/devis en € (hors coûts refacturés)",
                max_digits=10,
                verbose_name="montant (€ HT)",
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="number",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                verbose_name="numéro de facture/devis",
            ),
        ),
    ]
