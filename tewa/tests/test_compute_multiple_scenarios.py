# tewa/tests/test_compute_multiple_scenarios.py
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from tewa.models import (
    DefendedAsset,
    ModelParams,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)


class MultipleScenariosComputeTests(TestCase):
    def setUp(self):
        # Create 4 scenarios
        self.scenarios = []
        for i in range(1, 5):
            sc, _ = Scenario.objects.get_or_create(
                name=f"Scenario-{i}", start_time=timezone.now()
            )
            self.scenarios.append(sc)

            # Create one DA tied to this scenario
            DefendedAsset.objects.get_or_create(
                scenario=sc,
                name=f"DA-For-{sc.name}",
                lat=28.6139,
                lon=77.2090,
                radius_km=25.0,
            )

            # ModelParams for each scenario
            ModelParams.objects.get_or_create(
                scenario=sc,
                defaults=dict(
                    w_cpa=0.3, w_tcpa=0.3, w_tdb=0.2, w_twrp=0.2,
                    cpa_scale_km=20.0, tcpa_scale_s=120.0,
                    tdb_scale_km=30.0, twrp_scale_s=120.0,
                    clamp_0_1=True,
                )
            )

        # Seed 2 tracks (with samples) for scenarios 2–4 only
        for sc in self.scenarios[1:]:  # skip Scenario-1
            for t_idx in range(1, 3):
                trk = Track.objects.create(
                    scenario=sc,
                    track_id=f"T{sc.pk}-{t_idx}",
                    lat=28.7 + sc.pk * 0.01 + t_idx * 0.01,
                    lon=77.2 + sc.pk * 0.01 + t_idx * 0.01,
                    alt_m=3500 + t_idx * 100,
                    speed_mps=220 + t_idx * 10,
                    heading_deg=200 + t_idx * 5,
                )
                TrackSample.objects.create(
                    track=trk,
                    t=timezone.now(),
                    lat=trk.lat,
                    lon=trk.lon,
                    alt_m=trk.alt_m,
                    speed_mps=trk.speed_mps,
                    heading_deg=trk.heading_deg,
                )

    def test_compute_threats_for_all_scenarios(self):
        for sc in self.scenarios:
            # Prefer kwargs for call_command so option parsing is unambiguous
            call_command('compute_threats', scenario_id=sc.pk)

            scores = ThreatScore.objects.filter(scenario=sc)
            print(
                f"Scenario {sc.pk} ({sc.name}) -> {scores.count()} ThreatScore(s)")

            if sc is self.scenarios[0]:
                # Scenario-1 has no tracks; should produce 0 scores
                self.assertEqual(scores.count(), 0)
            else:
                # Scenarios 2–4 each have 2 tracks × 1 DA = 2 scores (or >= 1 if your command filters)
                self.assertGreaterEqual(scores.count(), 1)
