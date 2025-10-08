# tewa/services/threat_compute.py
from __future__ import annotations
from typing import List, Dict
from tewa.services import sampling, kinematics, normalize, scoring
from tewa.models import Track, ModelParams

from typing import Optional, cast

from django.utils import timezone

from core.utils.geodesy import LatLon, enu_from_latlon
from tewa.models import (
    DefendedAsset,
    ModelParams,  # still used by callers; conforms to ParamsLike
    Scenario,
    ThreatScore,
    Track,
)
from tewa.services.kinematics import (
    cpa_tcpa,
    time_to_weapon_release_s,
)
from tewa.services.normalize import clamp01, inv1
from tewa.types import ParamsLike

from datetime import timezone as dt_timezone

from datetime import timezone as dt_timezone
from django.utils import timezone  # keep if used


def _distance_km_to_da_center(da: DefendedAsset, lat: float, lon: float) -> float:
    e, n = enu_from_latlon(LatLon(lat, lon), LatLon(da.lat, da.lon))
    return (e * e + n * n) ** 0.5 / 1000.0


def score_components_to_threat(
    *,
    cpa_km: float | None,
    tcpa_s: float | None,
    tdb_km: float | None,
    twrp_s: float | None,
    params: dict[str, float],  # Accept a dictionary of params
) -> float:
    """
    Combine components into a single threat score.
    Convention: smaller is worse → higher normalized value with inv1().
    """
    # Use params dictionary for values
    n_cpa = inv1(cpa_km, params['cpa_scale_km'])

    tcpa_norm_src = tcpa_s if (tcpa_s is None or tcpa_s >= 0) else float("inf")
    n_tcpa = inv1(tcpa_norm_src, params['tcpa_scale_s'])

    n_tdb = inv1(tdb_km, params['tdb_scale_km'])

    twrp_norm_src = twrp_s if (twrp_s is None or twrp_s >= 0) else float("inf")
    n_twrp = inv1(twrp_norm_src, params['twrp_scale_s'])

    score = (
        params['w_cpa'] * n_cpa +
        params['w_tcpa'] * n_tcpa +
        params['w_tdb'] * n_tdb +
        params['w_twrp'] * n_twrp
    )
    return clamp01(score) if params['clamp_0_1'] else score


def compute_score_for_track(
    scenario: Scenario,
    da: DefendedAsset,
    track: Track,
    params: ParamsLike,  # Accept ParamsLike, which can be ModelParams or similar
    weapon_range_km: Optional[float] = None,
) -> ThreatScore:
    # Convert ParamsLike (ModelParams) to dictionary
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

    # 1) Kinematics (ENU-based)
    cpa = cpa_tcpa(
        lat_t=track.lat,
        lon_t=track.lon,
        spd_mps=track.speed_mps,
        hdg_deg=track.heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
    )

    # 2) Optional: time to DA boundary (seconds)
    twrpsecs = time_to_weapon_release_s(
        lat_t=track.lat,
        lon_t=track.lon,
        spd_mps=track.speed_mps,
        hdg_deg=track.heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
        weapon_range_km=weapon_range_km or da.radius_km,
    )

    # 3) Spatial urgency now (distance to DA center, km)
    tdb_km = _distance_km_to_da_center(da, track.lat, track.lon)

    # 4) Compute final score
    score = score_components_to_threat(
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrpsecs,
        params=params_dict,  # Pass the dictionary here
    )

    # 5) Persist
    return ThreatScore.objects.create(
        scenario=scenario,
        track=track,
        da=da,
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrpsecs,
        score=score,
        computed_at=timezone.now(),
    )


def batch_compute_for_scenario(
    scenario_id: int,
    da_id: int,
    weapon_range_km: float | None = None,
) -> list[ThreatScore]:
    scenario = Scenario.objects.get(id=scenario_id)
    da = DefendedAsset.objects.get(id=da_id)
    params, _ = ModelParams.objects.get_or_create(scenario=scenario)

    out: list[ThreatScore] = []
    for track in Track.objects.filter(scenario=scenario).iterator():
        out.append(
            compute_score_for_track(
                scenario, da, track, cast(ParamsLike, params), weapon_range_km
            )
        )
    return out


def compute_score_for_state(
    *,
    scenario: Scenario,
    da: DefendedAsset,
    track: Track,
    params: ParamsLike,  # Accept ParamsLike
    lat: float,
    lon: float,
    speed_mps: float,
    heading_deg: float,
    weapon_range_km: float | None = None,
) -> ThreatScore:
    # Convert ParamsLike (ModelParams) to dictionary
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

    # 1) Kinematics for supplied state
    cpa = cpa_tcpa(
        lat_t=lat,
        lon_t=lon,
        spd_mps=speed_mps,
        hdg_deg=heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
    )

    twrpsecs = time_to_weapon_release_s(
        lat_t=lat,
        lon_t=lon,
        spd_mps=speed_mps,
        hdg_deg=heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
        weapon_range_km=weapon_range_km or da.radius_km,
    )

    # 2) Spatial urgency now
    tdb_km = _distance_km_to_da_center(da, lat, lon)

    # 3) Final score calculation
    n_cpa = inv1(cpa.cpa_km, params_dict['cpa_scale_km'])
    n_tcpa = inv1(cpa.tcpa_s if (cpa.tcpa_s is None or cpa.tcpa_s >= 0)
                  else float("inf"), params_dict['tcpa_scale_s'])
    n_tdb = inv1(tdb_km, params_dict['tdb_scale_km'])
    n_twrp = inv1(twrpsecs if (twrpsecs is None or twrpsecs >= 0)
                  else float("inf"), params_dict['twrp_scale_s'])

    score = (
        params_dict['w_cpa'] * n_cpa
        + params_dict['w_tcpa'] * n_tcpa
        + params_dict['w_tdb'] * n_tdb
        + params_dict['w_twrp'] * n_twrp
    )
    if params_dict['clamp_0_1']:
        score = clamp01(score)

    # 4) Persist result
    return ThreatScore.objects.create(
        scenario=scenario,
        track=track,
        da=da,
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrpsecs,
        score=score,
        computed_at=timezone.now(),
    )


def _iso(dt):
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def calculate_scores_for_when(
    scenario, when, das, method: str = "linear", weapon_range_km: float = 20.0
) -> List[Dict]:
    """
    Pure compute (no persistence). Uses cpa_tcpa() + time_to_weapon_release_s()
    and the same ModelParams field names used elsewhere in this file:
      - weights: w_cpa, w_tcpa, w_tdb, w_twrp
      - scales:  cpa_scale_km, tcpa_scale_s, tdb_scale_km, twrp_scale_s
    TDB here is a spatial proxy: distance to DA center (km), like compute_score_for_track().
    """
    # Prefer scenario-scoped params; fallback to first row if not present
    params_obj = (
        ModelParams.objects.filter(scenario=scenario).first()
        or ModelParams.objects.first()
    )
    if not params_obj:
        return []

    # Convert params to a dict to avoid type-checker complaints
    P = {
        "w_cpa": float(params_obj.w_cpa),
        "w_tcpa": float(params_obj.w_tcpa),
        "w_tdb": float(params_obj.w_tdb),
        "w_twrp": float(params_obj.w_twrp),
        "cpa_scale_km": float(params_obj.cpa_scale_km),
        "tcpa_scale_s": float(params_obj.tcpa_scale_s),
        "tdb_scale_km": float(params_obj.tdb_scale_km),
        "twrp_scale_s": float(params_obj.twrp_scale_s),
        "clamp_0_1": bool(params_obj.clamp_0_1),
    }

    tracks = Track.objects.filter(scenario=scenario).only("id", "track_id")

    results: List[Dict] = []
    for tr in tracks:
        # must return dict or None
        state = sampling.get_state(tr, when=when, method=method)
        if not state:
            continue

        lat = state["lat"]
        lon = state["lon"]
        spd = state["speed_mps"]
        hdg = state["heading_deg"]

        # CPA/TCPA from current sampled state against each DA
        for da in das:
            cpa = cpa_tcpa(
                lat_t=lat, lon_t=lon,
                spd_mps=spd, hdg_deg=hdg,
                lat_da=da.lat, lon_da=da.lon,
            )
            # Spatial proxy for TDB (distance to DA center, km)
            tdb_km = _distance_km_to_da_center(da, lat, lon)

            # Time to weapon release (seconds)
            twrp_s = time_to_weapon_release_s(
                lat_t=lat, lon_t=lon,
                spd_mps=spd, hdg_deg=hdg,
                lat_da=da.lat, lon_da=da.lon,
                weapon_range_km=weapon_range_km or da.radius_km,
            )

            # Normalize with inv1 (same convention as earlier functions)
            n_cpa = inv1(cpa.cpa_km, P["cpa_scale_km"])
            n_tcpa = inv1(cpa.tcpa_s if (cpa.tcpa_s is None or cpa.tcpa_s >= 0) else float(
                "inf"), P["tcpa_scale_s"])
            n_tdb = inv1(tdb_km, P["tdb_scale_km"])
            n_twrp = inv1(twrp_s if (twrp_s is None or twrp_s >= 0)
                          else float("inf"), P["twrp_scale_s"])

            score = (
                P["w_cpa"] * n_cpa +
                P["w_tcpa"] * n_tcpa +
                P["w_tdb"] * n_tdb +
                P["w_twrp"] * n_twrp
            )
            if P["clamp_0_1"]:
                score = clamp01(score)

            results.append({
                "track_id": tr.track_id,
                "da_name": da.name,
                "score": round(float(score), 6),
                "components": {
                    "dcpa": cpa.cpa_km,
                    "tcpa": cpa.tcpa_s,
                    "tdb":  tdb_km,
                    "twrp": twrp_s,
                    "n_dcpa": n_cpa, "n_tcpa": n_tcpa, "n_tdb": n_tdb, "n_twrp": n_twrp
                },
                "sampled_at": _iso(state["sampled_at"]),
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
