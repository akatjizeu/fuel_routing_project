"""
    Management Command to Load & Geocode Stations
"""

import csv
from django.core.management.base import BaseCommand
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from routing.models import Station  # TheStation model

class Command(BaseCommand):
    help = 'Load stations from CSV and geocode them'

    def handle(self, *args, **options):
        geolocator = Nominatim(user_agent="fuel-routing")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

        with open('fuel-prices-for-be-assessment.csv', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Truckstop Name']
                addr = row['Address']
                city = row['City']
                state = row['State']
                price = float(row['Retail Price'])

                station, created = Station.objects.get_or_create(
                    name=name,
                    address=addr,
                    city=city,
                    state=state,
                    retail_price=price
                )
                if station.latitude is None:
                    location = geocode(f"{addr}, {city}, {state}, USA")
                    if location:
                        station.latitude = location.latitude
                        station.longitude = location.longitude
                        station.save()
                        self.stdout.write(f"Geocoded {station.name}")
