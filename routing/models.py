from django.db import models

# Create your models here.

"""
    The fuel station database table
"""

class Station(models.Model):
    objects = None
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2) # State abbreviation (e.g., CA)
    retail_price = models.FloatField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state})"

