# core/tests/test_kinematics.py
from __future__ import annotations

import math
from typing import cast

from django.test import SimpleTestCase

from tewa.services.kinematics import cpa_tcpa_km_s, tdb_s, twrp_s


class KinematicsTests(SimpleTestCase):
    def test_cpa_tcpa_basic(self) -> None:
        res = cpa_tcpa_km_s(
            da_lat=28.0, da_lon=77.0,
            trk_lat=28.0, trk_lon=77.1,  # ~10–11 km east
            speed_mps=200.0,
            heading_deg=180.0,  # south
        )
        self.assertTrue(res.cpa_km >= 0.0)
        self.assertTrue(math.isfinite(res.tcpa_s))

    def test_tdb_entry(self) -> None:
        t = tdb_s(
            da_lat=28.0, da_lon=77.0, da_radius_km=10.0,
            trk_lat=28.0, trk_lon=77.11,  # ~12 km east
            speed_mps=200.0,
            heading_deg=270.0,  # west, toward DA
        )
        # Prove to the type checker it's not None, then compare.
        self.assertIsNotNone(t)
        self.assertIsInstance(t, float)
        self.assertGreaterEqual(cast(float, t), 0.0)

    def test_twrp_none_when_moving_away(self) -> None:
        t = twrp_s(
            da_lat=28.0, da_lon=77.0, weapon_range_km=5.0,
            trk_lat=28.0, trk_lon=77.1,  # already east of DA
            speed_mps=250.0,
            heading_deg=90.0,  # further east (away)
        )
        self.assertIsNone(t)


def test_cpa():
    result = cpa_tcpa_km_s(
        da_lat=26.8890, da_lon=70.8640,
        trk_lat=28.9, trk_lon=77.4,
        speed_mps=220.0, heading_deg=200.0
    )
    assert result.cpa_km > 0
    assert result.tcpa_s >= 0


def test_tdb():
    result = tdb_s(
        da_lat=26.8890, da_lon=70.8640, da_radius_km=25.0,
        trk_lat=28.9, trk_lon=77.4,
        speed_mps=220.0, heading_deg=200.0
    )
    assert result is not None  # or assert result > 0 if it's expected to be non-zero
