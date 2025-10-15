# tewa/services/score_breakdown.py
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from django.utils.timezone import now

from tewa.models import DefendedAsset, ModelParams, Scenario, ThreatScore, Track
from tewa.services.kinematics import compute_cpa_tcpa_tdb_twrp
from tewa.services.scoring import _coerce_params, score_components_to_threat


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _coerce_float(x: Optional[float], default: float = 0.0) -> float:
    """Return a real float for scoring (no Nones into scorer)."""
    return float(x) if x is not None else float(default)


def _norm_positive(x: Optional[float], sigma: Optional[float]) -> Optional[float]:
    if x is None or sigma is None or sigma <= 0:
        return None
    return math.exp(-float(x) / float(sigma))


def _load_params_or_defaults(scenario: Scenario) -> Dict[str, float | bool]:
    defaults: Dict[str, float | bool] = dict(
        w_cpa=0.25, w_tcpa=0.25, w_tdb=0.25, w_twrp=0.25,
        sigma_cpa=1.0, sigma_tcpa=1.0, sigma_tdb=1.0, sigma_twrp=1.0,
    )
    try:
        mp = ModelParams.objects.filter(scenario=scenario).order_by(
            "-updated_at", "-id").first()
        return _coerce_params(mp) if mp else defaults  # type: ignore
    except Exception:
        return defaults


def get_score_breakdown(
    scenario_id: int,
    track_id: str,
    da_id: int,
    persist: bool = True,
    weapon_range_km: float = 10.0,
) -> Dict[str, object]:

    scenario = Scenario.objects.get(pk=scenario_id)
    track = Track.objects.get(scenario=scenario, track_id=track_id)
    da = DefendedAsset.objects.get(pk=da_id)

    params = _load_params_or_defaults(scenario)

    bundle = compute_cpa_tcpa_tdb_twrp(
        da_lat=da.lat,
        da_lon=da.lon,
        da_radius_km=da.radius_km,
        trk_lat=track.lat,
        trk_lon=track.lon,
        speed_mps=track.speed_mps,
        heading_deg=track.heading_deg,
        weapon_range_km=weapon_range_km,
    )

    # --- robust attribute access (some builds use tdb_s) ---
    cpa_km = _safe_float(getattr(bundle, "cpa_km", None))
    tcpa_s = _safe_float(getattr(bundle, "tcpa_s", None))
    tdb_km = _safe_float(
        getattr(bundle, "tdb_km", getattr(bundle, "tdb_s", None)))
    twrp_s = _safe_float(getattr(bundle, "twrp_s", None))

    # Per-component normalized values (optionals are fine here)
    n_cpa = _norm_positive(cpa_km,  _safe_float(
        params.get("sigma_cpa")))   # type: ignore[arg-type]
    n_tcpa = _norm_positive(tcpa_s,  _safe_float(
        params.get("sigma_tcpa")))  # type: ignore[arg-type]
    n_tdb = _norm_positive(tdb_km,  _safe_float(
        params.get("sigma_tdb")))   # type: ignore[arg-type]
    n_twrp = _norm_positive(twrp_s,  _safe_float(
        params.get("sigma_twrp")))  # type: ignore[arg-type]

    # --- coerce to real floats for the scorer (no Optional) ---
    cpa_f = _coerce_float(cpa_km)
    tcpa_f = _coerce_float(tcpa_s)
    tdb_f = _coerce_float(tdb_km)
    twrp_f = _coerce_float(twrp_s)

    final_score = score_components_to_threat(
        cpa_f, tcpa_f, tdb_f, twrp_f, params=params
    )

    computed_at = now()
    if persist:
        ThreatScore.objects.update_or_create(
            scenario=scenario,
            track=track,
            da=da,
            defaults={
                "cpa_km": cpa_km,
                "tcpa_s": tcpa_s,
                "tdb_km": tdb_km,
                "twrp_s": twrp_s,
                "score": final_score,
                "computed_at": computed_at,
            },
        )

    return {
        "scenario_id": scenario.id,
        "track_id": track.track_id,
        "da_id": da.id,
        "components": {
            "cpa_km": cpa_km,
            "tcpa_s": tcpa_s,
            "tdb_km": tdb_km,
            "twrp_s": twrp_s,
        },
        "normalized": {
            "cpa": n_cpa,
            "tcpa": n_tcpa,
            "tdb": n_tdb,
            "twrp": n_twrp,
        },
        "weights": {
            # type: ignore[arg-type]
            "w_cpa": _safe_float(params.get("w_cpa")),
            # type: ignore[arg-type]
            "w_tcpa": _safe_float(params.get("w_tcpa")),
            # type: ignore[arg-type]
            "w_tdb": _safe_float(params.get("w_tdb")),
            # type: ignore[arg-type]
            "w_twrp": _safe_float(params.get("w_twrp")),
        },
        "final_score": final_score,
        "computed_at": computed_at,
    }
