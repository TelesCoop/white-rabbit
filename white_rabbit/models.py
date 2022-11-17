from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


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


class Project(models.Model):
    class Meta:
        verbose_name = "projet"
        unique_together = ("lowercase_name", "company")

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
    is_client_project = models.BooleanField(verbose_name="Projet client", default=False)

    days_sold = models.DecimalField(
        verbose_name="Jours vendus",
        default=0,
        max_digits=4,
        decimal_places=1,
        help_text="Il s'agit du nombre de jours vendu au client pour ce projet",
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
        super().save(self, *args, **kwargs)

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
        default=8,
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

    def __str__(self):
        return self.name

    @property
    def name(self):
        if self.user.first_name:
            return f"{self.user.first_name} {self.user.last_name or ''}"
        return self.user.username
