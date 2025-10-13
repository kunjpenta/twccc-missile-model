# tewa/services/score_breakdown.py
from typing import Dict

from django.utils.timezone import now

from tewa.models import DefendedAsset, ModelParams, Scenario, ThreatScore, Track
from tewa.services.kinematics import compute_cpa_tcpa_tdb_twrp
from tewa.services.scoring import _coerce_params, score_components_to_threat


def get_score_breakdown(
    scenario_id: int,
    track_id: str,
    da_id: int,
    persist: bool = True,
    weapon_range_km: float = 10.0
) -> Dict[str, object]:
    """
    Compute and return the full score breakdown for a single Track × DA × Scenario.

    Returns:
        Dict with raw components, normalized values, final score, and computed timestamp.
    """

    # Fetch DB objects
    scenario = Scenario.objects.get(pk=scenario_id)
    track = Track.objects.get(scenario=scenario, track_id=track_id)
    da = DefendedAsset.objects.get(pk=da_id)
    params = ModelParams.objects.get(scenario=scenario)

    # Convert ModelParams to plain dict for type safety
    params_dict: Dict[str, float | bool] = _coerce_params(
        params)  # type: ignore

    # Compute raw kinematic components using keyword arguments
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

    cpa_km = bundle.cpa_km
    tcpa_s = bundle.tcpa_s
    tdb_km = bundle.tdb_s
    twrp_s = bundle.twrp_s

    # Compute normalized components
    s_cpa = score_components_to_threat(
        cpa_km, None, 0.0, 0.0, params=params_dict)
    s_tcpa = score_components_to_threat(
        0.0, tcpa_s, 0.0, 0.0, params=params_dict)
    s_tdb = score_components_to_threat(
        0.0, None, tdb_km, 0.0, params=params_dict)
    s_twrp = score_components_to_threat(
        0.0, None, 0.0, twrp_s, params=params_dict)

    # Final weighted score
    final_score = score_components_to_threat(
        cpa_km, tcpa_s, tdb_km, twrp_s, params=params_dict)

    # Persist if requested
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

    # Return breakdown dictionary
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
            "cpa": s_cpa,
            "tcpa": s_tcpa,
            "tdb": s_tdb,
            "twrp": s_twrp,
        },
        "final_score": final_score,
        "computed_at": computed_at,
    }
