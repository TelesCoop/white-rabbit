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


class Employee(models.Model):
    class Meta:
        ordering = ("name",)

    name = models.CharField(max_length=20)
    calendar_ical_url = models.CharField(max_length=150)
    availability_per_day = models.IntegerField(
        default=8, validators=[MinValueValidator(0), MaxValueValidator(24)]
    )

    def __str__(self):
        return self.name
