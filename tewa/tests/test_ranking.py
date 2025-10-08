# tewa/tests/test_ranking.py

from django.test import TestCase

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track
from tewa.services.ranking import rank_threats


class ThreatRankingTest(TestCase):

    def setUp(self):
        # Set up the test scenario, DAs, and tracks
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_time="2025-09-30T06:00:00Z",
            end_time=None,
            notes="Test scenario for ranking threats"
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

        # Create tracks for testing
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

        # Create ThreatScores for each track and DA
        ThreatScore.objects.create(
            scenario=self.scenario,
            da=self.da_alpha,
            track=self.track1,
            score=0.9,
            computed_at="2025-09-30T06:00:00Z"
        )
        ThreatScore.objects.create(
            scenario=self.scenario,
            da=self.da_alpha,
            track=self.track2,
            score=0.7,
            computed_at="2025-09-30T06:10:00Z"
        )
        ThreatScore.objects.create(
            scenario=self.scenario,
            da=self.da_bravo,
            track=self.track1,
            score=0.8,
            computed_at="2025-09-30T06:05:00Z"
        )

    def test_rank_threats_for_da(self):
        # Test DA-specific ranking
        ranked_threats = rank_threats(
            self.scenario.id, da_id=self.da_alpha.id, top_n=1)

        # Ensure that the correct threat is ranked for DA-Alpha
        self.assertEqual(len(ranked_threats), 1)
        self.assertEqual(ranked_threats[0]['da_name'], 'DA-Alpha')
        self.assertEqual(ranked_threats[0]['threats'][0]['track_id'], "T1")
        self.assertEqual(ranked_threats[0]['threats'][0]['score'], 0.9)

    def test_rank_threats_globally(self):
        # Test global ranking (across all DAs)
        ranked_threats = rank_threats(self.scenario.id, top_n=2)

        # Ensure that the global ranking includes threats from both DAs
        self.assertEqual(len(ranked_threats), 2)
        self.assertEqual(ranked_threats[0]['da_name'], 'DA-Alpha')
        self.assertEqual(ranked_threats[1]['da_name'], 'DA-Bravo')
