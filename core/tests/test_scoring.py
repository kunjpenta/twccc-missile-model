# core/tests/test_scoring.py
from __future__ import annotations

import math

from django.test import SimpleTestCase

from tewa.services.normalize import clamp01, inv1

# keep the positional-friendly one:
from tewa.services.scoring import score_components_to_threat  # keep this
from tewa.services.threat_compute import compute_threat_score

# (do NOT import score_components_to_threat here)


# ---- shared helper (one definition) ----
def _params_dict(*, clamp: bool = True) -> dict[str, float | bool]:
    return {
        "w_cpa": 0.25, "w_tcpa": 0.25, "w_tdb": 0.25, "w_twrp": 0.25,
        "cpa_scale_km": 20.0, "tcpa_scale_s": 120.0,
        "tdb_scale_km": 30.0, "twrp_scale_s": 120.0,
        "clamp_0_1": clamp,
    }


class ScoringTests(SimpleTestCase):
    """Pure-Python unit tests: no DB touch."""

    def test_inv1_basics(self):
        self.assertAlmostEqual(inv1(0, 10), 1.0)
        self.assertTrue(0.49 < inv1(10, 10) < 0.51)
        self.assertLess(inv1(100, 10), 0.1)
        self.assertEqual(inv1(None, 10), 0.0)
        self.assertEqual(inv1(float("inf"), 10), 0.0)
        self.assertEqual(inv1(-5, 10), 0.0)

    def test_clamp01(self):
        self.assertEqual(clamp01(-0.1), 0.0)
        self.assertEqual(clamp01(1.2), 1.0)
        self.assertEqual(clamp01(0.3), 0.3)
        self.assertEqual(clamp01(None), 0.0)

    def test_weighted_score(self):
        params = _params_dict()
        s = score_components_to_threat(
            cpa_km=5.0, tcpa_s=30.0, tdb_km=15.0, twrp_s=45.0, params=params
        )
        self.assertTrue(0.5 < s <= 1.0)

    def test_negative_tcpa_treated_as_far(self):
        params = _params_dict()
        s1 = score_components_to_threat(
            5.0, 30.0, 15.0, 45.0, params)  # type: ignore
        s2 = score_components_to_threat(
            5.0, -10.0, 15.0, 45.0, params)  # type: ignore
        self.assertLess(s2, s1)

    def test_weight_emphasis(self):
        params = {
            "w_cpa": 0.8, "w_tcpa": 0.1, "w_tdb": 0.05, "w_twrp": 0.05,
            "cpa_scale_km": 20.0, "tcpa_scale_s": 120.0,
            "tdb_scale_km": 30.0, "twrp_scale_s": 120.0,
            "clamp_0_1": True,
        }
        s_far = score_components_to_threat(
            40.0, 60.0, 25.0, 60.0, params)  # type: ignore
        s_near = score_components_to_threat(
            2.0,  60.0, 25.0, 60.0, params)  # type: ignore
        self.assertGreater(s_near, s_far)

    def test_compute_threat_score(self):
        params = _params_dict()
        result = compute_threat_score(
            da_lat=26.8890, da_lon=70.8640, da_radius_km=25.0,
            track_lat=28.9, track_lon=77.4,
            speed_mps=220.0, heading_deg=200.0,
            model_params=params,
        )
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)
        self.assertGreater(result["cpa_km"], 0.0)
        self.assertGreaterEqual(result["tcpa_s"], 0.0)


def test_twrp_none_still_returns_finite_score():
    params = _params_dict()
    result = compute_threat_score(
        da_lat=28.0, da_lon=77.0, da_radius_km=10.0,
        track_lat=28.0, track_lon=77.2,
        speed_mps=250.0, heading_deg=90.0,  # away
        model_params=params,
    )
    assert math.isfinite(result["score"])
    assert math.isinf(result["twrp_s"])     # service coerces None -> +inf
    assert result["score"] < 0.6


def test_no_clamp_allows_score_over_one():
    params = {
        "w_cpa": 0.4, "w_tcpa": 0.4, "w_tdb": 0.4, "w_twrp": 0.4,  # sum 1.6
        "cpa_scale_km": 20.0, "tcpa_scale_s": 120.0,
        "tdb_scale_km": 30.0, "twrp_scale_s": 120.0,
        "clamp_0_1": False,
    }
    s = score_components_to_threat(0.0, 0.0, 0.0, 0.0, params)  # type: ignore
    assert s > 1.0


def test_missing_params_use_defaults():
    params = {"w_cpa": 0.25, "w_tcpa": 0.25, "w_tdb": 0.25, "w_twrp": 0.25}
    s = score_components_to_threat(
        10.0, 60.0, 20.0, 60.0, params)  # type: ignore
    assert 0.0 <= s <= 1.0


def test_negative_tcpa_lowers_compute_score():
    params = _params_dict()
    a = compute_threat_score(
        da_lat=28.0, da_lon=77.0, da_radius_km=10.0,
        track_lat=28.0, track_lon=77.12,
        speed_mps=220.0, heading_deg=270.0,   # toward DA
        model_params=params,
    )
    b = compute_threat_score(
        da_lat=28.0, da_lon=77.0, da_radius_km=10.0,
        track_lat=28.0, track_lon=77.12,
        speed_mps=220.0, heading_deg=90.0,    # away (past CPA)
        model_params=params,
    )
    assert a["tcpa_s"] >= 0.0
    assert b["tcpa_s"] >= 0.0
    assert a["score"] > b["score"]


def test_extreme_distance_produces_low_score():
    params = _params_dict(clamp=True)
    s = score_components_to_threat(
        1200.0, 36000.0, 1200.0, 36000.0, params)  # type: ignore
    assert s < 0.1


def test_weights_not_normalized():
    base = _params_dict(clamp=False)
    dbl = {**base, "w_cpa": 0.5, "w_tcpa": 0.5, "w_tdb": 0.5, "w_twrp": 0.5}
    s1 = score_components_to_threat(0.0, 0.0, 0.0, 0.0, base)  # type: ignore
    s2 = score_components_to_threat(0.0, 0.0, 0.0, 0.0, dbl)  # type: ignore
    assert 1.95 <= (s2 / s1) <= 2.05
