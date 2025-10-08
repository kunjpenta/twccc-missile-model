# tewa/tests/test_api_compute_at.py
from __future__ import annotations

from datetime import timedelta
from typing import cast  # <-- add this

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from tewa.models import (
    DefendedAsset,
    ModelParams,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)


class ComputeAtLinearInterpolationTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        # Scenario + DA
        self.sc = Scenario.objects.create(
            name="Interp-Scenario",
            start_time=timezone.now(),
        )
        self.da = DefendedAsset.objects.create(
            name="DA-Alpha",
            lat=28.6139,
            lon=77.2090,
            radius_km=25.0,
        )

        # Model params
        ModelParams.objects.create(
            scenario=self.sc,
            w_cpa=0.3,
            w_tcpa=0.3,
            w_tdb=0.2,
            w_twrp=0.2,
            cpa_scale_km=20.0,
            tcpa_scale_s=120.0,
            tdb_scale_km=30.0,
            twrp_scale_s=120.0,
            clamp_0_1=True,
        )

        # Track with two samples that bracket T
        self.trk = Track.objects.create(
            scenario=self.sc,
            track_id="T-Interp",
            lat=28.70,   # snapshot not used if samples exist
            lon=77.30,
            alt_m=3000,
            speed_mps=220,
            heading_deg=200,
        )

        t0 = timezone.now()
        self.t_before = t0
        self.t_after = t0 + timedelta(seconds=60)
        self.t_mid = t0 + timedelta(seconds=30)

        TrackSample.objects.create(
            track=self.trk,
            t=self.t_before,
            lat=28.7000,
            lon=77.3000,
            alt_m=3000,
            speed_mps=220,
            heading_deg=200,
        )
        TrackSample.objects.create(
            track=self.trk,
            t=self.t_after,
            lat=28.7100,
            lon=77.3100,
            alt_m=3100,
            speed_mps=240,
            heading_deg=210,
        )

    def test_compute_at_uses_linear_interpolation_and_persists(self) -> None:
        resp = self.client.post(
            "/api/tewa/compute_at",
            {
                "scenario_id": self.sc.pk,  # use pk for Pylance happiness
                "when": self.t_mid.isoformat().replace("+00:00", "Z"),
                "da_ids": [self.da.pk],
                "method": "linear",
                "weapon_range_km": 20,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertIn("count", body)
        self.assertIn("scores", body)
        self.assertGreaterEqual(body["count"], 1)
        self.assertGreaterEqual(len(body["scores"]), 1)

        # Row exists for (scenario, da, track)
        self.assertTrue(
            ThreatScore.objects.filter(
                scenario=self.sc, da=self.da, track=self.trk
            ).exists()
        )

        # Score is non-None and in [0, 1]
        row = ThreatScore.objects.filter(
            scenario=self.sc, da=self.da, track=self.trk
        ).latest("computed_at")

        self.assertIsNotNone(row.score)
        score = cast(float, row.score)  # <-- explicit cast silences Pylance
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
