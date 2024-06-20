from datetime import datetime
from enum import Enum

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from white_rabbit.constants import DEFAULT_NB_WORKING_HOURS


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.

    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateField(auto_now=True)

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    class Meta:
        verbose_name = "entreprise"

    name = models.CharField(max_length=20)
    admins = models.ManyToManyField(User, related_name="companies")

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


PROJECT_CATEGORIES_CHOICES = (
    (ProjectCategories.PRO_BONO.value, "Pro-bono"),
    (ProjectCategories.CLIENT.value, "Client"),
    (ProjectCategories.INTERNAL.value, "Interne"),
    (ProjectCategories.ROLE.value, "Rôle"),
    (ProjectCategories.OTHER.value, "Autre"),
    (ProjectCategories.OFF_WORK.value, "Congé"),
    ("", "Non défini"),
)


class Project(models.Model):
    class Meta:
        verbose_name = "projet"
        unique_together = (
            "lowercase_name",
            "name",
            "company",
            "category",
            "start_date",
            "end_date",
        )

    company = models.ForeignKey(
        Company,
        verbose_name="entreprise",
        related_name="projects",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=32, verbose_name="nom")
    lowercase_name = models.CharField(
        max_length=32, verbose_name="nom en minuscule", null=False
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    category = models.CharField(
        choices=PROJECT_CATEGORIES_CHOICES, blank=True, max_length=12
    )
    estimated_days_count = models.DecimalField(
        verbose_name="Jours prévus",
        default=0,
        max_digits=4,
        decimal_places=1,
        help_text="Nombre de jours prévus sur le projet",
    )

    def save(self, *args, **kwargs):
        self.lowercase_name = self.name.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Alias(models.Model):
    class Meta:
        verbose_name = "alias"

    project = models.ForeignKey(
        Project, verbose_name="projet", related_name="aliases", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=32, verbose_name="nom")
    lowercase_name = models.CharField(
        max_length=32, verbose_name="nom en minuscule", null=False
    )

    def save(self, *args, **kwargs):
        self.lowercase_name = self.name.lower()
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
        help_text="Pour une journée incomplète, ce total est utilisé pour calculer la proportion d'une journée passée sur un projet",
    )
    min_working_hours_for_full_day = models.DecimalField(
        verbose_name="nb heures journée complète",
        max_digits=3,
        decimal_places=1,
        default=6,
        help_text="Nombre d'heures de travail à partir au-delà duquel on considère une journée complète",
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
