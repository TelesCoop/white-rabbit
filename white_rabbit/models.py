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


class Employee(TimeStampedModel):
    class Meta:
        verbose_name = "salarié"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    calendar_ical_url = models.CharField(
        verbose_name="URL calendrier Google",
        max_length=150,
        help_text='appelée "Adresse publique au format iCal"',
    )
    availability_per_day = models.IntegerField(
        verbose_name="heure travaillées par jour",
        default=8,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    company = models.ForeignKey(
        Company, verbose_name="entreprise", on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return self.name

    @property
    def name(self):
        if self.user.first_name:
            return f"{self.user.first_name} {self.user.last_name or ''}"
        return self.user.username
