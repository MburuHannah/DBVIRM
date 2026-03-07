from django.db import models
from django.conf import settings


class Unit(models.Model):
    UNIT_STATUS = (
        ('Vacant', 'Vacant'),
        ('Occupied', 'Occupied'),
    )

    HOUSE_TYPE = (
        ('Single Room', 'Single Room'),
        ('Bedsitter', 'Bedsitter'),
        ('1 Bedroom', '1 Bedroom'),
        ('2 Bedroom', '2 Bedroom'),
    )

    # Make the foreign key explicit and allow null temporarily
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_units',
        null=True,  # Add this temporarily to avoid errors with existing data
        blank=True
    )

    unit_name = models.CharField(max_length=50)
    house_type = models.CharField(max_length=50, choices=HOUSE_TYPE)
    rent = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=UNIT_STATUS, default='Vacant')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.unit_name