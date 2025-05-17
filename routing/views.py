#from django.shortcuts import render
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from routing.models import Station
from routing.utils import haversine

# Create your views here.


@require_GET
def route_view(request):
    #Parse input addresses
    start_addr = request.GET.get('start')
    end_addr = request.GET.get('end')
    if not start_addr or not end_addr:
        return JsonResponse({'error': 'Please provide start and end query parameters.'}, status=400)

    #Geocode start & end
    geolocator = Nominatim(user_agent="fuel-routing")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    start_loc = geocode(f"{start_addr}, USA")
    end_loc = geocode(f"{end_addr}, USA")
    if not start_loc or not end_loc:
        return JsonResponse({'error': 'Geocoding failed for one or both locations.'}, status=400)
    start_coord = (start_loc.latitude, start_loc.longitude)
    end_coord = (end_loc.latitude, end_loc.longitude)

    # Call OSRM for route geometry
    osrm_url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}"
        f"?overview=full&geometries=geojson"
    )
    osrm_resp = requests.get(osrm_url)
    if osrm_resp.status_code != 200:
        return JsonResponse({'error': 'Routing API error.'}, status=502)
    data = osrm_resp.json()
    route = data['routes'][0]
    coords = route['geometry']['coordinates']  # list of [lon, lat]
    #total_distance = route['distance'*]
    total_distance = route['distance']         # in meters

    #Determine fueling stops every 500 miles (500 mi ≈ 804672 m)
    range_m = 500 * 1609.34
    stops = []
    cum_dist = 0.0
    last_pt = start_coord

    for lon, lat in coords:
        this_pt = (lat, lon)
        segment = haversine(last_pt, this_pt)
        cum_dist += segment
        if cum_dist >= range_m:
            # find cheapest station within 20 km of this_pt
            buffer_deg = 0.2  # rough ~20 km
            nearby = Station.objects.filter(
                latitude__range=(lat-buffer_deg, lat+buffer_deg),
                longitude__range=(lon-buffer_deg, lon+buffer_deg)
            )
            best = None
            for s in nearby:
                dist_to_pt = haversine((s.latitude, s.longitude), this_pt)
                if dist_to_pt <= 20000:  # 20 km
                    if best is None or s.retail_price < best.retail_price:
                        best = s
            if best:
                # record stop
                stops.append({
                    'name': best.name,
                    'latitude': best.latitude,
                    'longitude': best.longitude,
                    'price': best.retail_price,
                    'segment_distance_m': cum_dist,
                })
                # reset
                last_pt = (best.latitude, best.longitude)
                cum_dist = 0.0

    #Calculate costs
    mpg = 10.0
    total_cost = 0.0
    for stop in stops:
        dist_m = stop['segment_distance_m']
        gallons = (dist_m/1000) / 1.60934 / mpg
        cost = gallons * stop['price']
        stop['cost'] = round(cost, 2)
        total_cost += cost
    total_cost = round(total_cost, 2)

    #Build response
    return JsonResponse({
        'route': {
            'geometry': route['geometry'],  # GeoJSON geometry
            'distance_m': total_distance,
            'duration_s': route['duration'],
        },
        'fuel_stops': stops,
        'total_cost': total_cost,
    })

