# tewa/tests/test_ranking.py

from django.test import TestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track
from tewa.services.ranking import rank_threats


class ThreatRankingTest(TestCase):
    def setUp(self):
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_time=timezone.now(),
            notes="Test scenario for ranking threats",
        )

        # ✅ Attach DAs to the scenario (FK is non-nullable)
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

        self.track1 = Track.objects.create(
            scenario=self.scenario,
            track_id="T1",
            lat=28.9,
            lon=77.4,
            alt_m=3500,
            speed_mps=220.0,
            heading_deg=200.0,
        )
        self.track2 = Track.objects.create(
            scenario=self.scenario,
            track_id="T2",
            lat=28.7,
            lon=77.1,
            alt_m=3200,
            speed_mps=250.0,
            heading_deg=170.0,
        )

        # Use timezone-aware datetimes
        ts1 = parse_datetime("2025-09-30T06:00:00Z")
        ts2 = parse_datetime("2025-09-30T06:10:00Z")
        ts3 = parse_datetime("2025-09-30T06:05:00Z")

        ThreatScore.objects.create(
            scenario=self.scenario,
            da=self.da_alpha,
            track=self.track1,
            score=0.9,
            computed_at=ts1,
        )
        ThreatScore.objects.create(
            scenario=self.scenario,
            da=self.da_alpha,
            track=self.track2,
            score=0.7,
            computed_at=ts2,
        )
        ThreatScore.objects.create(
            scenario=self.scenario,
            da=self.da_bravo,
            track=self.track1,
            score=0.8,
            computed_at=ts3,
        )

    def test_rank_threats_for_da(self):
        ranked = rank_threats(
            self.scenario.id, da_id=self.da_alpha.id, top_n=1)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["da_name"], "DA-Alpha")
        self.assertEqual(ranked[0]["threats"][0]["track_id"], "T1")
        self.assertEqual(ranked[0]["threats"][0]["score"], 0.9)

    def test_rank_threats_globally(self):
        ranked = rank_threats(self.scenario.id, top_n=2)

        # Expect both DAs present, DA-Alpha first due to higher top score (0.9 > 0.8)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["da_name"], "DA-Alpha")
        self.assertEqual(ranked[1]["da_name"], "DA-Bravo")
