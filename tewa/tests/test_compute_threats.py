# tewa/tests/test_compute_threats.py

from django.test import TestCase

from tewa.management.commands.compute_threats import Command
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track


class ComputeThreatsTest(TestCase):

    def setUp(self):
        # Set up your test data here
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_time="2025-09-30T06:00:00Z",
            end_time=None,
            notes="Test scenario for compute threats"
        )
        self.da_alpha = DefendedAsset.objects.create(
            name="DA-Alpha",
            lat=26.889045927834,
            lon=70.86392327099402,
            radius_km=25.0
        )
        self.da_bravo = DefendedAsset.objects.create(
            name="DA-Bravo",
            lat=26.2389,
            lon=73.0243,
            radius_km=30.0
        )

        # Create some tracks for testing
        self.track1 = Track.objects.create(
            scenario=self.scenario,
            track_id="T1",
            lat=28.9,
            lon=77.4,
            alt_m=3500,
            speed_mps=220.0,
            heading_deg=200.0
        )
        self.track2 = Track.objects.create(
            scenario=self.scenario,
            track_id="T2",
            lat=28.7,
            lon=77.1,
            alt_m=3200,
            speed_mps=250.0,
            heading_deg=170.0
        )

    def test_compute_threats(self):
        # Pass the scenario_id and da_id when calling the command
        command = Command()

        # Pass both scenario_id and da_id as part of the command options
        options = {
            'scenario_id': self.scenario.id,
            'da_id': self.da_alpha.id,  # Example with DA-Alpha
        }
        command.handle(**options)  # Run the command with the options

        # Verify threat scores are created
        threat_scores = ThreatScore.objects.filter(
            scenario=self.scenario, da=self.da_alpha)
        self.assertEqual(threat_scores.count(), 2)

        # Check threat score details
        threat_score = threat_scores.first()

        # Debug: print computed raw components
        print(f"CPA: {threat_score.cpa_km}, TCPA: {threat_score.tcpa_s}, TDB: {threat_score.tdb_km}, TWRP: {threat_score.twrp_s}")

        # Check DA and score association
        self.assertEqual(threat_score.da.name, "DA-Alpha")
        # Debug the computed score
        print(f"Computed threat score: {threat_score.score}")
        # Ensure score is positive (valid)
        self.assertGreater(threat_score.score, 0)
