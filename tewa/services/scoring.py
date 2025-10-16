# tewa/services/scoring.py
from __future__ import annotations
from decimal import ROUND_HALF_UP, Decimal

import math
from typing import Any, Mapping, Optional, Union, cast

from tewa.services.normalize import clamp01, inv1
from tewa.types import ModelParamsDict, ModelParamsIn, ParamLike

# -------------------------------------------------------------------
# Core parameter coercion & normalization utilities
# -------------------------------------------------------------------


def normalize(value: float, scale: float, clamp: bool = True) -> float:
    """
    Normalize a value against a given scale into [0, 1].
    Example: value=10, scale=100 → 0.9.
    If clamp=True, output is clipped to [0,1].
    """
    if scale <= 0:
        raise ValueError("Scale must be positive")

    normalized = 1.0 - (value / scale)
    return max(0.0, min(1.0, normalized)) if clamp else normalized


def _coerce_params(p: Union[ParamLike, Mapping[str, Any]]) -> ModelParamsDict:
    """
    Coerce input parameters (dict or ORM object) into a fully populated ModelParamsDict.
    Guarantees all expected keys and float/bool coercion for safety.
    """
    # ORM-style object with attributes
    if not isinstance(p, Mapping) and hasattr(p, "w_cpa"):
        return {
            "w_cpa": float(p.w_cpa),
            "w_tcpa": float(p.w_tcpa),
            "w_tdb": float(p.w_tdb),
            "w_twrp": float(p.w_twrp),
            "cpa_scale_km": float(p.cpa_scale_km),
            "tcpa_scale_s": float(p.tcpa_scale_s),
            "tdb_scale_km": float(p.tdb_scale_km),
            "twrp_scale_s": float(p.twrp_scale_s),
            "clamp_0_1": bool(p.clamp_0_1),
        }

    # Dict-like (may be partial)
    m = cast(ModelParamsIn, p)
    return {
        "w_cpa": float(m.get("w_cpa", 0.25)),
        "w_tcpa": float(m.get("w_tcpa", 0.25)),
        "w_tdb": float(m.get("w_tdb", 0.25)),
        "w_twrp": float(m.get("w_twrp", 0.25)),
        "cpa_scale_km": float(m.get("cpa_scale_km", 20.0)),
        "tcpa_scale_s": float(m.get("tcpa_scale_s", 120.0)),
        "tdb_scale_km": float(m.get("tdb_scale_km", 30.0)),
        "twrp_scale_s": float(m.get("twrp_scale_s", 120.0)),
        "clamp_0_1": bool(m.get("clamp_0_1", True)),
    }


def _is_bad(v: Optional[float]) -> bool:
    """Return True if v is None, NaN, or infinite."""
    return v is None or not math.isfinite(v)


# -------------------------------------------------------------------
# Threat scoring kernels
# -------------------------------------------------------------------

def score_components_to_threat(
    cpa_km: float,
    tcpa_s: Optional[float],
    tdb_km: float,
    twrp_s: Optional[float],
    params: ParamLike,
) -> float:
    """
    Compute normalized threat score from weighted CPA, TCPA, TDB, TWRP components.

    All components are inverted via inv1(scale) for consistency with the
    compute_threat_score() pipeline. Negative TCPA/TWRP values are treated as
    past or invalid → score 0.
    """
    p = _coerce_params(params)

    # Normalized components
    s_cpa = inv1(cpa_km, p["cpa_scale_km"])
    s_tcpa = 0.0 if (tcpa_s is not None and tcpa_s <
                     0) else inv1(tcpa_s, p["tcpa_scale_s"])
    s_tdb = inv1(tdb_km, p["tdb_scale_km"])
    s_twrp = 0.0 if (twrp_s is not None and twrp_s <
                     0) else inv1(twrp_s, p["twrp_scale_s"])

    # Weighted sum
    score = (
        p["w_cpa"] * s_cpa
        + p["w_tcpa"] * s_tcpa
        + p["w_tdb"] * s_tdb
        + p["w_twrp"] * s_twrp
    )

    return clamp01(score) if p["clamp_0_1"] else float(score)


def combine_score(
    *,
    cpa_km: float,
    tcpa_s: float,
    tdb_s: Optional[float],
    twrp_s: Optional[float],
) -> float:
    """
    Legacy/simple combination of normalized scores using static weights.
    Used for quick sanity checks or visualization, not full TEWA computation.
    """
    weights = {"cpa": 0.4, "tcpa": 0.3, "tdb": 0.2, "twrp": 0.1}

    cpa_n = normalize(max(0.0, cpa_km), 100.0, clamp=True)
    tcpa_n = 0.0 if (not math.isfinite(tcpa_s) or tcpa_s <
                     0) else normalize(tcpa_s, 300.0, clamp=True)
    tdb_n = 0.0 if (tdb_s is None or not math.isfinite(tdb_s)
                    or tdb_s < 0) else normalize(tdb_s, 30.0, clamp=True)
    twrp_n = 0.0 if (twrp_s is None or not math.isfinite(
        twrp_s) or twrp_s < 0) else normalize(twrp_s, 60.0, clamp=True)

    final_score = (
        weights["cpa"] * cpa_n
        + weights["tcpa"] * tcpa_n
        + weights["tdb"] * tdb_n
        + weights["twrp"] * twrp_n
    )

    return max(0.0, min(1.0, final_score))


__all__ = [
    "normalize",
    "_coerce_params",
    "_is_bad",
    "score_components_to_threat",
    "combine_score",
]

# tewa/services/scoring.py


def _round6(val):
    return float(Decimal(str(val)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
