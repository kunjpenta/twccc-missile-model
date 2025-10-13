# tewa/services/threat_compute.py


from __future__ import annotations
from typing import Any, Mapping, Optional, Union

from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Mapping, Optional, Union, cast

from django.utils import timezone

from core.utils.geodesy import LatLon, enu_from_latlon
from tewa.models import (
    DefendedAsset,
    ModelParams,  # conforms to ParamLike
    Scenario,
    ThreatScore,
    Track,
)
from tewa.services import sampling
from tewa.services.kinematics import cpa_tcpa, time_to_weapon_release_s
from tewa.services.normalize import clamp01, inv1
from tewa.services.scoring import (
    _coerce_params,  # shared coercer (dict or ORM)
)
from tewa.services.scoring import (
    score_components_to_threat as _score_components_to_threat,  # canonical impl
)
from tewa.types import ModelParamsDict, ParamLike, ParamsLike


# ------------------------
# small helpers
# ------------------------
def _distance_km_to_da_center(da: DefendedAsset, lat: float, lon: float) -> float:
    e, n = enu_from_latlon(LatLon(lat, lon), LatLon(da.lat, da.lon))
    return (e * e + n * n) ** 0.5 / 1000.0


def _distance_km_latlon(da_lat: float, da_lon: float, lat: float, lon: float) -> float:
    e, n = enu_from_latlon(LatLon(lat, lon), LatLon(da_lat, da_lon))
    return (e * e + n * n) ** 0.5 / 1000.0


def _iso(dt):
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


# ------------------------
# public API
# ------------------------
def compute_threat_score(
    *,
    da_lat: float,
    da_lon: float,
    da_radius_km: float,
    track_lat: float,
    track_lon: float,
    speed_mps: float,
    heading_deg: float,
    model_params: Union[ParamLike, Mapping[str, Any]],
    weapon_range_km: Optional[float] = None,
) -> dict[str, float]:
    """
    Compute normalized threat score from CPA/TCPA/TDB/TWRP using parameter weights.
    Returns: {"cpa_km","tcpa_s","tdb_km","twrp_s","score"}
    """
    p = _coerce_params(model_params)

    # Raw components
    cpa = cpa_tcpa(
        lat_t=track_lat,
        lon_t=track_lon,
        spd_mps=speed_mps,
        hdg_deg=heading_deg,
        lat_da=da_lat,
        lon_da=da_lon,
    )
    tdb_km = _distance_km_latlon(da_lat, da_lon, track_lat, track_lon)
    twrp_s_val = time_to_weapon_release_s(
        lat_t=track_lat,
        lon_t=track_lon,
        spd_mps=speed_mps,
        hdg_deg=heading_deg,
        lat_da=da_lat,
        lon_da=da_lon,
        weapon_range_km=(weapon_range_km or da_radius_km),
    )

    # Scales (defaults safe)
    cpa_scale_km = float(p.get("cpa_scale_km", 20.0))
    tcpa_scale_s = float(p.get("tcpa_scale_s", 120.0))
    tdb_scale_km = float(p.get("tdb_scale_km", 30.0))
    twrp_scale_s = float(p.get("twrp_scale_s", 120.0))

    # Negative TCPA => “past” → treat as far by normalizing as None
    tcpa_for_norm = None if (
        cpa.tcpa_s is not None and cpa.tcpa_s < 0) else cpa.tcpa_s

    n_cpa = inv1(cpa.cpa_km, cpa_scale_km)
    n_tcpa = inv1(tcpa_for_norm, tcpa_scale_s)
    n_tdb = inv1(tdb_km, tdb_scale_km)
    n_twrp = inv1(twrp_s_val, twrp_scale_s)

    w_cpa = float(p.get("w_cpa", 0.25))
    w_tcpa = float(p.get("w_tcpa", 0.25))
    w_tdb = float(p.get("w_tdb", 0.25))
    w_twrp = float(p.get("w_twrp", 0.25))
    clamp = bool(p.get("clamp_0_1", True))

    score = w_cpa * n_cpa + w_tcpa * n_tcpa + w_tdb * n_tdb + w_twrp * n_twrp
    if clamp:
        score = clamp01(score)

    # Coerce outputs: tcpa >= 0; twrp as +inf when None
    tcpa_s_ret: float = cpa.tcpa_s if (
        cpa.tcpa_s is not None and cpa.tcpa_s >= 0.0) else 0.0
    twrp_s_ret: float = float("inf") if (
        twrp_s_val is None) else float(twrp_s_val)

    return {
        "cpa_km": float(cpa.cpa_km),
        "tcpa_s": tcpa_s_ret,
        "tdb_km": float(tdb_km),
        "twrp_s": twrp_s_ret,
        "score": float(score),
    }


def score_components_to_threat(
    cpa_km: float,
    tcpa_s: Optional[float],
    tdb_km: float,
    twrp_s: Optional[float],
    params: Union[ParamLike, Mapping[str, Any]],
) -> float:
    """
    Positional-friendly wrapper so tests (and other callers) can pass either a dict
    or a Django model for params. Delegates to the canonical implementation.
    """
    return _score_components_to_threat(
        cpa_km=cpa_km,
        tcpa_s=tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrp_s,
        params=params,
    )


def compute_score_for_track(
    scenario: Scenario,
    da: DefendedAsset,
    track: Track,
    params: Union[ParamLike, Mapping[str, Any]],
    weapon_range_km: Optional[float] = None,
) -> ThreatScore:
    # 1) Normalize params (accepts dict or ModelParams-like)
    p = _coerce_params(params)

    # Guard against legacy/empty rows with all-zero weights
    if (p["w_cpa"] + p["w_tcpa"] + p["w_tdb"] + p["w_twrp"]) == 0.0:
        p["w_cpa"] = p["w_tcpa"] = p["w_tdb"] = p["w_twrp"] = 0.25

    # 2) Kinematics
    cpa = cpa_tcpa(
        lat_t=track.lat,
        lon_t=track.lon,
        spd_mps=track.speed_mps,
        hdg_deg=track.heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
    )

    twrp_s_val = time_to_weapon_release_s(
        lat_t=track.lat,
        lon_t=track.lon,
        spd_mps=track.speed_mps,
        hdg_deg=track.heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
        weapon_range_km=weapon_range_km or da.radius_km,
    )

    tdb_km = _distance_km_to_da_center(da, track.lat, track.lon)

    # 3) Final score (handles None/negative components internally)
    score = score_components_to_threat(
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrp_s_val,
        params=p,
    )

    # 4) Persist
    return ThreatScore.objects.create(
        scenario=scenario,
        track=track,
        da=da,
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrp_s_val,
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

    # Ensure new ModelParams gets non-zero defaults
    params, _ = ModelParams.objects.get_or_create(
        scenario=scenario,
        defaults={
            "w_cpa": 0.25, "w_tcpa": 0.25, "w_tdb": 0.25, "w_twrp": 0.25,
            "cpa_scale_km": 20.0, "tcpa_scale_s": 120.0,
            "tdb_scale_km": 30.0, "twrp_scale_s": 120.0,
            "clamp_0_1": True,
        },
    )

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
    params: Union[ParamLike, Mapping[str, Any]],
    lat: float,
    lon: float,
    speed_mps: float,
    heading_deg: float,
    weapon_range_km: float | None = None,
) -> ThreatScore:
    p = _coerce_params(params)

    # Kinematics for supplied state
    cpa = cpa_tcpa(
        lat_t=lat,
        lon_t=lon,
        spd_mps=speed_mps,
        hdg_deg=heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
    )
    twrp_s_val = time_to_weapon_release_s(
        lat_t=lat,
        lon_t=lon,
        spd_mps=speed_mps,
        hdg_deg=heading_deg,
        lat_da=da.lat,
        lon_da=da.lon,
        weapon_range_km=weapon_range_km or da.radius_km,
    )
    tdb_km = _distance_km_to_da_center(da, lat, lon)

    score = score_components_to_threat(
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrp_s_val,
        params=p,
    )

    return ThreatScore.objects.create(
        scenario=scenario,
        track=track,
        da=da,
        cpa_km=cpa.cpa_km,
        tcpa_s=cpa.tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrp_s_val,
        score=score,
        computed_at=timezone.now(),
    )


def calculate_scores_for_when(
    scenario: Scenario,
    when,
    das: list[DefendedAsset],
    method: str = "linear",
    weapon_range_km: float = 20.0,
) -> List[Dict]:
    """
    Pure compute (no persistence). Uses cpa_tcpa() + time_to_weapon_release_s()
    and the same ModelParams field names:
      - weights: w_cpa, w_tcpa, w_tdb, w_twrp
      - scales:  cpa_scale_km, tcpa_scale_s, tdb_scale_km, twrp_scale_s
    TDB here is distance to DA center (km), matching compute_score_for_track().
    """
    params_obj = (
        ModelParams.objects.filter(scenario=scenario).first()
        or ModelParams.objects.first()
    )
    if not params_obj:
        return []

    P = _coerce_params(params_obj)

    tracks = Track.objects.filter(scenario=scenario).only("id", "track_id")
    results: List[Dict] = []

    for tr in tracks:
        state = sampling.get_state(tr, when=when, method=method)
        if not state:
            continue

        lat = state["lat"]
        lon = state["lon"]
        spd = state["speed_mps"]
        hdg = state["heading_deg"]

        for da in das:
            cpa = cpa_tcpa(
                lat_t=lat, lon_t=lon, spd_mps=spd, hdg_deg=hdg,
                lat_da=da.lat, lon_da=da.lon,
            )
            tdb_km = _distance_km_to_da_center(da, lat, lon)
            twrp_s_val = time_to_weapon_release_s(
                lat_t=lat, lon_t=lon, spd_mps=spd, hdg_deg=hdg,
                lat_da=da.lat, lon_da=da.lon,
                weapon_range_km=weapon_range_km or da.radius_km,
            )

            n_cpa = inv1(cpa.cpa_km, P["cpa_scale_km"])
            n_tcpa = inv1(
                cpa.tcpa_s if (cpa.tcpa_s is None or cpa.tcpa_s >=
                               0) else float("inf"),
                P["tcpa_scale_s"],
            )
            n_tdb = inv1(tdb_km, P["tdb_scale_km"])
            n_twrp = inv1(
                twrp_s_val if (twrp_s_val is None or twrp_s_val >=
                               0) else float("inf"),
                P["twrp_scale_s"],
            )

            score = (
                P["w_cpa"] * n_cpa
                + P["w_tcpa"] * n_tcpa
                + P["w_tdb"] * n_tdb
                + P["w_twrp"] * n_twrp
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
                    "tdb": tdb_km,
                    "twrp": twrp_s_val,
                    "n_dcpa": n_cpa,
                    "n_tcpa": n_tcpa,
                    "n_tdb": n_tdb,
                    "n_twrp": n_twrp,
                },
                "sampled_at": _iso(state["sampled_at"]),
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
