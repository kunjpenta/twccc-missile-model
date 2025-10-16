# tewa/tests/factories.py

import random

from tewa.models import DefendedAsset, Scenario, Track


def create_scenario(name="Scenario-3"):
    return Scenario.objects.create(name=name)


def create_da(scenario, name="DA1", lat=0.0, lon=0.0, radius_km=5.0):
    return DefendedAsset.objects.create(
        scenario=scenario,
        name=name,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )


def create_tracks(scenario, n=3):
    tracks = []
    for i in range(n):
        tracks.append(
            Track.objects.create(
                scenario=scenario,
                track_id=f"T{i+1}",
                lat=random.uniform(-1, 1),
                lon=random.uniform(-1, 1),
                alt_m=random.uniform(500, 1500),
                speed_mps=random.uniform(150, 300),
                heading_deg=random.uniform(0, 360),
            )
        )
    return tracks
