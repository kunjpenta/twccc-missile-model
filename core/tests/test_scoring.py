# core/tests/test_scoring.py
from __future__ import annotations

from django.test import SimpleTestCase

from tewa.models import ModelParams, Scenario
from tewa.services.normalize import clamp01, inv1
from tewa.services.scoring import compute_threat_score
from tewa.services.threat_compute import score_components_to_threat


class ScoringTests(SimpleTestCase):
    def _params(self) -> ModelParams:
        # Unsaved instances are fine for type checking & pure-Python tests.
        sc = Scenario(id=1, name="Test-Scenario")
        return ModelParams(
            scenario=sc,
            w_cpa=0.25, w_tcpa=0.25, w_tdb=0.25, w_twrp=0.25,
            cpa_scale_km=20.0, tcpa_scale_s=120.0, tdb_scale_km=30.0, twrp_scale_s=120.0,
            clamp_0_1=True,
        )

    def test_inv1_basics(self):
        self.assertAlmostEqual(inv1(0, 10), 1.0)
        self.assertTrue(0.49 < inv1(10, 10) < 0.51)   # ~0.5
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
    params = self._params()  # This is your ModelParams instance

    # Convert ModelParams to a dictionary of float values
    params_dict = {
        'w_cpa': float(params.w_cpa),
        'w_tcpa': float(params.w_tcpa),
        'w_tdb': float(params.w_tdb),
        'w_twrp': float(params.w_twrp),
        'cpa_scale_km': float(params.cpa_scale_km),
        'tcpa_scale_s': float(params.tcpa_scale_s),
        'tdb_scale_km': float(params.tdb_scale_km),
        'twrp_scale_s': float(params.twrp_scale_s),
        'clamp_0_1': params.clamp_0_1,
    }

    # Call the function with the dictionary instead of the ModelParams instance
    s = score_components_to_threat(
        cpa_km=5.0,          # close
        tcpa_s=30.0,         # soon
        tdb_km=15.0,         # moderate center distance (km)
        twrp_s=45.0,         # soon-ish
        params=params_dict,  # Pass the dictionary of float values
    )

    self.assertTrue(0.5 < s <= 1.0)

    def test_negative_tcpa_treated_as_far(self):
        params = self._params()
        s1 = score_components_to_threat(
            cpa_km=5.0, tcpa_s=30.0, tdb_km=15.0, twrp_s=45.0, params=params
        )
        # Negative TCPA -> treat as "in the past" (∞ urgency) => normalized ~0
        s2 = score_components_to_threat(
            cpa_km=5.0, tcpa_s=-10.0, tdb_km=15.0, twrp_s=45.0, params=params
        )
        self.assertLess(s2, s1)

    def test_weight_emphasis(self):
        sc = Scenario(id=1, name="Test-Scenario")
        params = ModelParams(
            scenario=sc,
            w_cpa=0.8, w_tcpa=0.1, w_tdb=0.05, w_twrp=0.05,
            cpa_scale_km=20.0, tcpa_scale_s=120.0, tdb_scale_km=30.0, twrp_scale_s=120.0,
            clamp_0_1=True,
        )
        s_far = score_components_to_threat(
            cpa_km=40.0, tcpa_s=60.0, tdb_km=25.0, twrp_s=60.0, params=params
        )
        s_near = score_components_to_threat(
            cpa_km=2.0, tcpa_s=60.0, tdb_km=25.0, twrp_s=60.0, params=params
        )
        self.assertGreater(s_near, s_far)


def test_compute_threat_score():
    model_params = ModelParams.objects.get(id=1)

    # Convert ModelParams to a dictionary of float values
    params_dict = {
        'w_cpa': float(model_params.w_cpa),
        'w_tcpa': float(model_params.w_tcpa),
        'w_tdb': float(model_params.w_tdb),
        'w_twrp': float(model_params.w_twrp),
        'cpa_scale_km': float(model_params.cpa_scale_km),
        'tcpa_scale_s': float(model_params.tcpa_scale_s),
        'tdb_scale_km': float(model_params.tdb_scale_km),
        'twrp_scale_s': float(model_params.twrp_scale_s),
        'clamp_0_1': model_params.clamp_0_1,
    }

    result = compute_threat_score(
        da_lat=26.8890, da_lon=70.8640, da_radius_km=25.0,
        track_lat=28.9, track_lon=77.4,
        speed_mps=220.0, heading_deg=200.0,
        model_params=params_dict  # Pass the dictionary of float values
    )

    assert 0 <= result['score'] <= 1
    assert result['cpa_km'] > 0
    assert result['tcpa_s'] >= 0
