# Generated by Django 5.0.6 on 2025-01-14 16:03

from django.db import migrations

def add_invoices(apps, schema_editor):
    Invoice = apps.get_model("white_rabbit", "Invoice")
    Project = apps.get_model("white_rabbit", "Project")
    for project in Project.objects.filter(total_sold__gt=0):
        date = project.created
        Invoice.objects.create(
            number=f"{date.year}-{date.month} {project.name} AUTO",
            project=project,
            amount=project.total_sold,
            days_count=project.estimated_days_count,
            date=date,
            comment="générée automatiquement lors d'une migration"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("white_rabbit", "0038_invoice"),
    ]

    operations = [
        migrations.RunPython(add_invoices, reverse_code=migrations.RunPython.noop),
    ]
