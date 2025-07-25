from datetime import datetime
from enum import Enum

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint
from django.utils.safestring import mark_safe

from white_rabbit.constants import DEFAULT_NB_WORKING_HOURS
from white_rabbit.text_utils import normalize_name


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.

    """

    created = models.DateTimeField(auto_now_add=True, verbose_name="créé le")
    modified = models.DateField(auto_now=True, verbose_name="modifié le")

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    class Meta:
        verbose_name = "entreprise"

    name = models.CharField(max_length=20)
    admins = models.ManyToManyField(User, related_name="companies")

    daily_employee_cost = models.DecimalField(
        verbose_name="Coût salarié journalier moyen",
        default=0,
        max_digits=6,
        decimal_places=2,
        help_text="Coût journalier moyen d'un salarié pour l'entreprise en € (salaire moyen brut chargé / nb jours travaillés)",
    )
    profitability_threshold = models.DecimalField(
        verbose_name="Seuil de rentabilité",
        default=0,
        max_digits=6,
        decimal_places=2,
        help_text="Le seuil journalier de rentabilité, en €, prend en compte que tous les jours ne sont pas travaillés (commercial, formation) et intègre les coûts de structure (support, loyer, logiciels...)",
    )
    daily_market_price = models.DecimalField(
        verbose_name="Prix du marché",
        default=0,
        max_digits=6,
        decimal_places=2,
        help_text="Tarif journalier moyen exercé sur le marché en €",
    )

    def __str__(self):
        return self.name

    def is_admin(self, user: User):
        return self.admins.filter(pk=user.pk).exists()


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


PROJECT_CATEGORIES_CHOICES = (
    (ProjectCategories.PRO_BONO.value, "Pro-bono"),
    (ProjectCategories.CLIENT.value, "Client"),
    (ProjectCategories.INTERNAL.value, "Interne"),
    (ProjectCategories.ROLE.value, "Rôle"),
    (ProjectCategories.OTHER.value, "Autre"),
    (ProjectCategories.OFF_WORK.value, "Congé"),
    (ProjectCategories.OKLM.value, "Oklm"),
    (ProjectCategories.SALES.value, "Commercial"),
    (ProjectCategories.FORMATION.value, "Formation"),
    ("", "Non défini"),
)

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


class Category(TimeStampedModel):
    class Meta:
        verbose_name = "Catégorie"
        unique_together = ("name", "company")

    name = models.CharField(max_length=32, verbose_name="nom")
    company = models.ForeignKey(
        Company,
        verbose_name="entreprise",
        related_name="categories",
        on_delete=models.CASCADE,
    )
    is_working_time = models.BooleanField(
        verbose_name="est du temps de travail",
        default=True,
        help_text="La catégorie est-elle un temps de travail ? Décocher par exemple pour les congés.",
    )
    color = models.CharField(
        max_length=32,
        verbose_name="couleur",
        default="bg-yellow-100",
        help_text=mark_safe(
            "Couleur de la catégorie, <a href= 'https://tailwindcss.com/docs/background-color'>référence</a>"
        ),
    )

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class Invoice(TimeStampedModel):
    class Meta:
        verbose_name = "facture/devis"

    number = models.CharField(
        max_length=100, verbose_name="numéro de facture/devis", null=True, blank=True
    )
    date = models.DateField(verbose_name="date")
    project = models.ForeignKey(
        "Project",
        verbose_name="projet",
        related_name="invoices",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(
        verbose_name="montant (€ HT)",
        max_digits=10,
        decimal_places=2,
        help_text="Montant facture/devis en € (hors coûts refacturés)",
    )
    days_count = models.DecimalField(
        verbose_name="jours",
        max_digits=4,
        decimal_places=1,
        help_text="Nombre de jours facturés",
    )
    comment = models.CharField(
        verbose_name="commentaire", blank=True, max_length=200, null=True
    )

    def __str__(self):
        return f"{self.number} ({self.date})"


class Project(TimeStampedModel):
    class Meta:
        verbose_name = "projet"
        constraints = [
            UniqueConstraint(
                name="project name",
                fields=[
                    "name",
                    "company",
                    "start_date",
                    "is_forecast",
                ],
                nulls_distinct=False,
            )
        ]

    company = models.ForeignKey(
        Company,
        verbose_name="entreprise",
        related_name="projects",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=32, verbose_name="nom")
    notes = models.TextField(verbose_name="notes", blank=True)
    lowercase_name = models.CharField(
        max_length=32, verbose_name="nom en minuscule", null=False
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    category = models.ForeignKey(
        Category,
        verbose_name="catégorie",
        related_name="projects",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    estimated_days_count = models.DecimalField(
        verbose_name="Jours prévus",
        default=0,
        max_digits=4,
        decimal_places=1,
        help_text="Nombre de jours prévus sur le projet",
    )
    total_sold = models.DecimalField(
        verbose_name="Prix total de vente (€ HT)",
        default=0,
        max_digits=10,
        decimal_places=2,
        help_text="Montant total vendu pour le projet en € (hors coûts refacturés)",
    )
    is_forecast = models.BooleanField(
        verbose_name="Prévision", default=False, help_text="Projet prévisionnel"
    )

    def update_total_sold_and_days_from_invoices(self):
        invoices = self.invoices.all()
        self.total_sold = sum(invoice.amount for invoice in invoices)
        self.estimated_days_count = sum(invoice.days_count for invoice in invoices)

    def save(self, *args, **kwargs):
        self.lowercase_name = normalize_name(self.name)
        if self.is_forecast:
            super().save(*args, **kwargs)
            return
        if not self.pk:
            super().save(*args, **kwargs)
            self.update_total_sold_and_days_from_invoices()
            super().save()
            return
        self.update_total_sold_and_days_from_invoices()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.start_date:
            return f"{self.name} ({self.start_date}{f' - {self.end_date}' if self.end_date else ''})"
        return self.name


class ForecastProject(Project):
    forecast_employees = models.ManyToManyField(
        "Employee",
        through="EmployeeForecastAssignment",
        verbose_name="employés prévisionnels",
        blank=True,
        help_text="Employés affectés à ce projet prévisionnel",
    )

    def clean(self):
        """Validate forecast project data"""
        super().clean()

        # Require start_date and end_date for forecast projects
        if not self.start_date:
            raise ValidationError(
                {
                    "start_date": "La date de début est obligatoire pour les projets prévisionnels."
                }
            )

        if not self.end_date:
            raise ValidationError(
                {
                    "end_date": "La date de fin est obligatoire pour les projets prévisionnels."
                }
            )

        # Validate that end_date is after start_date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(
                {
                    "end_date": "La date de fin ne peut pas être antérieure à la date de début."
                }
            )

    class Meta:
        verbose_name = "projet prévisionnel"
        verbose_name_plural = "projets prévisionnels"


class Alias(models.Model):
    class Meta:
        verbose_name = "alias"

    project = models.ForeignKey(
        Project, verbose_name="projet", related_name="aliases", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100, verbose_name="nom")
    lowercase_name = models.CharField(
        max_length=32, verbose_name="nom en minuscule", null=False
    )

    def save(self, *args, **kwargs):
        self.lowercase_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Employee(TimeStampedModel):
    class Meta:
        verbose_name = "salarié"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    calendar_ical_url = models.CharField(
        verbose_name="URL calendrier Google",
        max_length=256,
        help_text='"Adresse publique au format iCal" si le calendrier est public, sinon "Adresse secrète au format iCal"',
    )
    default_day_working_hours = models.IntegerField(
        verbose_name="heures travaillées par jour",
        default=DEFAULT_NB_WORKING_HOURS,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="En forfait jour, pour une journée incomplète, ce total est utilisé pour calculer la proportion d'une journée passée sur un projet. En forfait heures, c'est le nombre d'heures travaillées par jour.",
    )
    min_working_hours_for_full_day = models.DecimalField(
        verbose_name="nb heures journée complète",
        max_digits=3,
        decimal_places=1,
        default=6,
        help_text="Nombre d'heures de travail à partir au-delà duquel on considère une journée complète",
    )
    is_paid_hourly = models.BooleanField(
        verbose_name="forfait heure",
        help_text="si coché, le calcul des jours est au pro-rata d'une journée de travail complète, donc un jour de travail peut être compté comme moins d'un jour, voire plusieurs jours",
        default=False,
    )
    company = models.ForeignKey(
        Company,
        verbose_name="entreprise",
        on_delete=models.CASCADE,
        null=True,
        related_name="employees",
    )
    start_time_tracking_from = models.DateField(
        verbose_name="Début du suivi de temps",
        default=datetime.now,
        null=True,
        blank=True,
        help_text="Pour désactiver le suivi du temps, laisser ce champ vide",
    )
    end_time_tracking_on = models.DateField(
        verbose_name="Fin du suivi de temps",
        null=True,
        blank=True,
        help_text="Date de fin de contrat d'un salarié, le cas échéant",
    )
    works_day_1 = models.BooleanField(verbose_name="travaille le lundi", default=True)
    works_day_2 = models.BooleanField(verbose_name="travaille le mardi", default=True)
    works_day_3 = models.BooleanField(
        verbose_name="travaille le mercredi", default=True
    )
    works_day_4 = models.BooleanField(verbose_name="travaille le jeudi", default=True)
    works_day_5 = models.BooleanField(
        verbose_name="travaille le vendredi", default=True
    )
    works_day_6 = models.BooleanField(verbose_name="travaille le samedi", default=False)
    works_day_7 = models.BooleanField(
        verbose_name="travaille le dimanche", default=False
    )
    disabled = models.BooleanField(
        verbose_name="désactivé", default=False, help_text="Salarié désactivé"
    )

    def __str__(self):
        return self.name

    @property
    def name(self):
        if self.user.first_name:
            return f"{self.user.first_name} {self.user.last_name or ''}"
        return self.user.username

    @property
    def forecast_projects(self):
        return ForecastProject.objects.filter(
            employee_assignments__employee=self
        ).distinct()


class EmployeeForecastAssignment(models.Model):
    employee = models.ForeignKey(
        "Employee", on_delete=models.CASCADE, related_name="forecast_assignments"
    )
    forecast_project = models.ForeignKey(
        "ForecastProject", on_delete=models.CASCADE, related_name="employee_assignments"
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Laisser vide pour utiliser la date de début du projet prévisionnel",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Laisser vide pour utiliser la date de fin du projet prévisionnel",
    )

    estimated_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Nombre total de jours estimés pour cet employé sur ce projet",
        validators=[MinValueValidator(0.1)],
    )

    def clean(self):
        """Validate assignment data"""
        if not self.forecast_project or not self.employee:
            return

        # Skip validation if objects are not yet saved (during creation)
        if not self.forecast_project.pk or not self.employee.pk:
            return

        self._validate_company_consistency()
        self._validate_assignment_dates()
        self._validate_estimated_days()

    def _validate_company_consistency(self):
        """Validate that employee and project belong to the same company"""
        if self.employee.company != self.forecast_project.company:
            raise ValidationError(
                {
                    "employee": f"L'employé {self.employee.name} appartient à l'entreprise "
                    f"{self.employee.company.name}, mais le projet appartient à "
                    f"{self.forecast_project.company.name}. Un employé ne peut être "
                    f"assigné qu'à un projet de son entreprise."
                }
            )

    def _validate_assignment_dates(self):
        """Validate assignment dates against project dates"""
        project_start = self.forecast_project.start_date
        project_end = self.forecast_project.end_date

        # If project has no dates, can't validate
        if not project_start or not project_end:
            return

        self._validate_start_date(project_start, project_end)
        self._validate_end_date(project_start, project_end)
        self._validate_date_order()

    def _validate_start_date(self, project_start, project_end):
        """Validate assignment start date"""
        if not self.start_date:
            return

        if self.start_date < project_start:
            raise ValidationError(
                {
                    "start_date": f'La date de début ({self.start_date.strftime("%d/%m/%Y")}) '
                    f"ne peut pas être antérieure à la date de début du projet "
                    f'({project_start.strftime("%d/%m/%Y")})'
                }
            )
        if self.start_date > project_end:
            raise ValidationError(
                {
                    "start_date": f'La date de début ({self.start_date.strftime("%d/%m/%Y")}) '
                    f"ne peut pas être postérieure à la date de fin du projet "
                    f'({project_end.strftime("%d/%m/%Y")})'
                }
            )

    def _validate_end_date(self, project_start, project_end):
        """Validate assignment end date"""
        if not self.end_date:
            return

        if self.end_date < project_start:
            raise ValidationError(
                {
                    "end_date": f'La date de fin ({self.end_date.strftime("%d/%m/%Y")}) '
                    f"ne peut pas être antérieure à la date de début du projet "
                    f'({project_start.strftime("%d/%m/%Y")})'
                }
            )
        if self.end_date > project_end:
            raise ValidationError(
                {
                    "end_date": f'La date de fin ({self.end_date.strftime("%d/%m/%Y")}) '
                    f"ne peut pas être postérieure à la date de fin du projet "
                    f'({project_end.strftime("%d/%m/%Y")})'
                }
            )

    def _validate_date_order(self):
        """Validate that start_date <= end_date if both are provided"""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(
                {
                    "end_date": f'La date de fin ({self.end_date.strftime("%d/%m/%Y")}) '
                    f"ne peut pas être antérieure à la date de début "
                    f'({self.start_date.strftime("%d/%m/%Y")})'
                }
            )

    def _validate_estimated_days(self):
        """Validate that total assigned days don't exceed project's estimated days"""
        if self.forecast_project.estimated_days_count <= 0:
            return

        # Get all existing assignments for this project, excluding the current one
        existing_assignments = EmployeeForecastAssignment.objects.filter(
            forecast_project=self.forecast_project
        )
        if self.pk:
            existing_assignments = existing_assignments.exclude(pk=self.pk)

        # Calculate total assigned days
        total_assigned = sum(
            float(assignment.estimated_days) for assignment in existing_assignments
        )
        total_assigned += float(self.estimated_days)

        project_total = float(self.forecast_project.estimated_days_count)

        if total_assigned > project_total:
            raise ValidationError(
                {
                    "estimated_days": f"Le total des jours assignés ({total_assigned:.1f}) "
                    f"dépasse le nombre de jours prévus du projet ({project_total:.1f}). "
                    f"Jours déjà assignés: {total_assigned - float(self.estimated_days):.1f}"
                }
            )

    class Meta:
        verbose_name = "Affectation prévisionnelle"
        verbose_name_plural = "Affectations prévisionnelles"
        unique_together = ("employee", "forecast_project", "start_date")

    def __str__(self):
        return f"{self.employee.name} → {self.forecast_project.name} ({self.start_date} - {self.end_date})"
