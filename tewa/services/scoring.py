# tewa/services/scoring.py

from typing import Optional

from tewa.models import ModelParams
from tewa.services.kinematics import CPAResult, cpa_tcpa_km_s, tdb_s, twrp_s


def normalize(value: float, scale: float, clamp: bool = True) -> float:
    """
    Normalize a raw value to 0..1 using the provided scale.
    For distances: smaller values = higher threat → invert by 1 - (value/scale)
    """
    if scale <= 0:
        raise ValueError("Scale must be positive")

    normalized = 1.0 - (value / scale)
    if clamp:
        normalized = max(0.0, min(1.0, normalized))
    return normalized


def compute_threat_score(
    *,
    da_lat: float,
    da_lon: float,
    da_radius_km: float,
    track_lat: float,
    track_lon: float,
    speed_mps: float,
    heading_deg: float,
    model_params: ModelParams,
    # Made optional instead of default 0.0
    weapon_range_km: Optional[float] = None,
) -> dict:
    """
    Compute normalized threat score from CPA/TCPA/TDB/TWRP using ModelParams weights.
    Returns a dictionary with:
        cpa, tcpa, tdb, twrp, weighted_score
    """

    # ---------------------------
    # 1) Compute raw components
    # ---------------------------
    cpa_tcpa_res: CPAResult = cpa_tcpa_km_s(
        da_lat=da_lat, da_lon=da_lon,
        trk_lat=track_lat, trk_lon=track_lon,
        speed_mps=speed_mps, heading_deg=heading_deg
    )
    tdb_val_s = tdb_s(
        da_lat=da_lat, da_lon=da_lon, da_radius_km=da_radius_km,
        trk_lat=track_lat, trk_lon=track_lon,
        speed_mps=speed_mps, heading_deg=heading_deg
    )
    twrp_val_s = twrp_s(
        # Use 0.0 only if None
        da_lat=da_lat, da_lon=da_lon, weapon_range_km=weapon_range_km or 0.0,
        trk_lat=track_lat, trk_lon=track_lon,
        speed_mps=speed_mps, heading_deg=heading_deg
    )

    # ---------------------------
    # 2) Normalize each component
    # ---------------------------
    cpa_norm = normalize(cpa_tcpa_res.cpa_km,
                         model_params.cpa_scale_km, model_params.clamp_0_1)
    tcpa_norm = normalize(cpa_tcpa_res.tcpa_s,
                          model_params.tcpa_scale_s, model_params.clamp_0_1)
    tdb_norm = normalize(tdb_val_s if tdb_val_s is not None else model_params.tdb_scale_km,
                         model_params.tdb_scale_km, model_params.clamp_0_1)
    twrp_norm = normalize(twrp_val_s if twrp_val_s is not None else model_params.twrp_scale_s,
                          model_params.twrp_scale_s, model_params.clamp_0_1)

    # ---------------------------
    # 3) Weighted score
    # ---------------------------
    weighted_score = (
        cpa_norm * model_params.w_cpa +
        tcpa_norm * model_params.w_tcpa +
        tdb_norm * model_params.w_tdb +
        twrp_norm * model_params.w_twrp
    )

    return {
        "cpa_km": cpa_tcpa_res.cpa_km,
        "tcpa_s": cpa_tcpa_res.tcpa_s,
        "tdb_km": tdb_val_s,
        "twrp_s": twrp_val_s,
        "score": weighted_score
    }


def combine_score(
    *,
    cpa_km: float,
    tcpa_s: float,
    tdb_s: Optional[float],
    twrp_s: Optional[float],
) -> float:
    """
    Combine normalized CPA, TCPA, TDB, and TWRP values into a final threat score.
    Weights can be adjusted here based on the importance of each component.

    The final score will be a weighted sum of these components. Lower values for
    CPA, TCPA, TDB, and TWRP mean higher threat, so we use 1 - (value / scale) for normalization.
    """
    # Example weights (can be tuned as needed)
    weights = {
        "cpa": 0.4,  # Higher weight on CPA as it represents the closest approach
        "tcpa": 0.3,
        "tdb": 0.2,
        "twrp": 0.1,
    }

    # Normalize each component (inverted to ensure lower values = higher threat)
    # Assuming max CPA distance of 100 km
    normalized_cpa = 1.0 - (cpa_km / 100.0)
    # Assuming max TCPA time of 300 seconds
    normalized_tcpa = 1.0 - (tcpa_s / 300.0)
    normalized_tdb = 1.0 if tdb_s is None else 1.0 - \
        (tdb_s / 30.0)  # Assuming max TDB distance of 30 km
    normalized_twrp = 1.0 if twrp_s is None else 1.0 - \
        (twrp_s / 60.0)  # Assuming max TWRP time of 60 seconds

    # Apply weights to each component and calculate final score
    final_score = (
        normalized_cpa * weights["cpa"] +
        normalized_tcpa * weights["tcpa"] +
        normalized_tdb * weights["tdb"] +
        normalized_twrp * weights["twrp"]
    )

    # Ensure the score is between 0 and 1
    return max(0.0, min(final_score, 1.0))
