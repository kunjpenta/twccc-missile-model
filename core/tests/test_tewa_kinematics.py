# core/tests/test_tewa_kinematics.py
from __future__ import annotations

import math
from typing import cast

from django.test import SimpleTestCase

from tewa.services.kinematics import cpa_tcpa_km_s, tdb_s, twrp_s


class KinematicsTests(SimpleTestCase):
    def test_cpa_tcpa_basic(self):
        res = cpa_tcpa_km_s(
            da_lat=28.6, da_lon=77.2,
            trk_lat=28.7, trk_lon=77.3,
            speed_mps=200.0,
            heading_deg=180.0,  # south
        )
        self.assertGreaterEqual(res.cpa_km, 0.0)
        self.assertTrue(math.isfinite(res.tcpa_s) or math.isinf(res.tcpa_s))

    def test_tdb_entry(self):
        t = tdb_s(
            da_lat=28.6, da_lon=77.2, da_radius_km=10.0,
            trk_lat=28.6, trk_lon=77.31,  # ~12km east
            speed_mps=200.0,
            heading_deg=270.0,  # west
        )
        self.assertIsNotNone(t)
        t_float = cast(float, t)
        self.assertGreaterEqual(t_float, 0.0)

    def test_twrp_none_when_moving_away(self):
        t = twrp_s(
            da_lat=28.6, da_lon=77.2, weapon_range_km=5.0,
            trk_lat=28.6, trk_lon=77.30,
            speed_mps=250.0,
            heading_deg=90.0,  # east
        )
        self.assertIsNone(t)
