from pyhafas import HafasClient
from pyhafas.profile import DBProfile

client = HafasClient(DBProfile())

print("Searching for stations...")
for name in ["Buchenau", "Fürstenfeldbruck"]:
    stations = client.locations(name)
    if stations:
        print(f"Found {name}: {stations[0].name} (ID: {stations[0].id})")
    else:
        print(f"Not found: {name}")

print("\nFetching departures for Buchenau...")
try:
    # Use Buchenau ID if found (likely 8001156 based on previous knowledge)
    buchenau = client.locations("Buchenau")[0]
    departures = client.departures(
        station=buchenau.id,
        duration=60,
        products={
            'long_distance_express': False,
            'long_distance': False,
            'regional_express': False,
            'regional': False,
            'suburban': True,  # S-Bahn
            'bus': False,
            'ferry': False,
            'subway': False,
            'tram': False,
            'taxi': False
        }
    )
    print(f"Found {len(departures)} departures")
    for d in departures[:3]:
        print(f"{d.name} at {d.dateTime} delay: {d.delay}")
except Exception as e:
    print(f"Error: {e}")
