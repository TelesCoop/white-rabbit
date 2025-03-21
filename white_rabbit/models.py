from datetime import datetime
from enum import Enum

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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

    def update_total_sold_and_days_from_invoices(self):
        invoices = self.invoices.all()
        self.total_sold = sum(invoice.amount for invoice in invoices)
        self.estimated_days_count = sum(invoice.days_count for invoice in invoices)

    def save(self, *args, **kwargs):
        self.lowercase_name = normalize_name(self.name)
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
