# tewa/management/commands/seed_demo.py

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from tewa.models import DefendedAsset, ModelParams, Scenario, Track, TrackSample


class Command(BaseCommand):
    help = "Seed demo scenario, defended assets, tracks, and parameters (idempotent)."

    def handle(self, *args, **options):
        sc, _ = Scenario.objects.get_or_create(
            name="Demo-Scenario",
            defaults={"start_time": timezone.now(
            ), "notes": "Seeded via seed_demo."},
        )

        da1, _ = DefendedAsset.objects.get_or_create(
            name="DA-Alpha (Jaisalmer)",
            # defaults={"lat": 28.6139, "lon": 77.2090, "radius_km": 25.0},
            defaults={"lat": 26.890177579521072,
                      "lon": 70.86510754467697, "radius_km": 25.0},
        )
        da2, _ = DefendedAsset.objects.get_or_create(
            name="DA-Bravo (Jodhpur)",
            defaults={"lat": 26.2389, "lon": 73.0243, "radius_km": 30.0},
        )

        ModelParams.objects.get_or_create(
            scenario=sc,
            defaults=dict(
                w_cpa=0.30, w_tcpa=0.30, w_tdb=0.20, w_twrp=0.20,
                cpa_scale_km=20.0, tcpa_scale_s=120.0, tdb_scale_km=30.0, twrp_scale_s=120.0,
                clamp_0_1=True,
            ),
        )

        tracks = [
            dict(track_id="T1", lat=28.9000, lon=77.4000,
                 alt_m=3500.0, speed_mps=220.0, heading_deg=200.0),
            dict(track_id="T2", lat=28.7000, lon=77.1000,
                 alt_m=3200.0, speed_mps=250.0, heading_deg=170.0),
            dict(track_id="T3", lat=28.5000, lon=77.6000,
                 alt_m=4800.0, speed_mps=210.0, heading_deg=315.0),
        ]
        for t in tracks:
            trk, created = Track.objects.get_or_create(
                scenario=sc, track_id=t["track_id"],
                defaults=t
            )
            if not created:
                # keep latest snapshot updated
                for k, v in t.items():
                    setattr(trk, k, v)
                trk.save()

            TrackSample.objects.get_or_create(
                track=trk, t=timezone.now(),
                defaults=dict(lat=trk.lat, lon=trk.lon, alt_m=trk.alt_m,
                              speed_mps=trk.speed_mps, heading_deg=trk.heading_deg)
            )

        self.stdout.write(self.style.SUCCESS(
            "Seeded Demo-Scenario, DAs, Tracks, ModelParams"))
