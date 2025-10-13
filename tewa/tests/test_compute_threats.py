# tewa/tests/test_compute_threats.py
from django.test import TestCase
from django.utils import timezone

from tewa.management.commands.compute_threats import Command
from tewa.models import DefendedAsset, ModelParams, Scenario, ThreatScore, Track


class ComputeThreatsTest(TestCase):
    def setUp(self):
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_time=timezone.now(),
            notes="Test scenario for compute threats",
        )

        # ✅ tie DAs to the scenario (required FK)
        self.da_alpha = DefendedAsset.objects.create(
            scenario=self.scenario,
            name="DA-Alpha",
            lat=26.889045927834,
            lon=70.86392327099402,
            radius_km=25.0,
        )
        self.da_bravo = DefendedAsset.objects.create(
            scenario=self.scenario,
            name="DA-Bravo",
            lat=26.2389,
            lon=73.0243,
            radius_km=30.0,
        )

        # ✅ ensure params exist for this scenario (many services expect it)
        ModelParams.objects.get_or_create(
            scenario=self.scenario,
            defaults=dict(
                w_cpa=0.25, w_tcpa=0.25, w_tdb=0.25, w_twrp=0.25,
                cpa_scale_km=20.0, tcpa_scale_s=120.0,
                tdb_scale_km=30.0, twrp_scale_s=120.0,
                clamp_0_1=True,
            )
        )

        # Tracks for this scenario
        self.track1 = Track.objects.create(
            scenario=self.scenario,
            track_id="T1",
            lat=28.9, lon=77.4,
            alt_m=3500, speed_mps=220.0, heading_deg=200.0,
        )
        self.track2 = Track.objects.create(
            scenario=self.scenario,
            track_id="T2",
            lat=28.7, lon=77.1,
            alt_m=3200, speed_mps=250.0, heading_deg=170.0,
        )

    def test_compute_threats(self):
        command = Command()
        options = {"scenario_id": self.scenario.id, "da_id": self.da_alpha.id}
        command.handle(**options)

        threat_scores = ThreatScore.objects.filter(
            scenario=self.scenario, da=self.da_alpha
        )
        self.assertEqual(threat_scores.count(), 2)

        ts = threat_scores.first()
        self.assertEqual(ts.da.name, "DA-Alpha")
        self.assertGreater(ts.score, 0)
