# tewa/services/threat_computes.py

from __future__ import annotations

from datetime import timezone as dt_timezone
from time import time
from typing import Any, Dict, List, Mapping, Optional, Union, cast

from django.utils import timezone

from core.utils.geodesy import LatLon, enu_from_latlon
from tewa.models import DefendedAsset, ModelParams, Scenario, ThreatScore, Track
from tewa.services import sampling
from tewa.services.kinematics import compute_cpa_tcpa_tdb_twrp
from tewa.services.normalize import clamp01, inv1
from tewa.services.scoring import _coerce_params
from tewa.services.scoring import (
    score_components_to_threat as _score_components_to_threat,
)
from tewa.types import ParamLike, ParamsLike


# ------------------------
# small helpers
# ------------------------
def _distance_km_to_da_center(da: DefendedAsset, lat: float, lon: float) -> float:
    e, n = enu_from_latlon(LatLon(lat, lon), LatLon(da.lat, da.lon))
    return (e * e + n * n) ** 0.5 / 1000.0


def _iso(dt):
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


# ------------------------
# core threat computation
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
    model_params: Union[Mapping[str, Any], ModelParams],
    weapon_range_km: Optional[float] = None,
) -> dict[str, float]:
    """
    Compute normalized threat score from CPA/TCPA/TDB/TWRP using parameter weights.
    Returns: {"cpa_km","tcpa_s","tdb_km","twrp_s","score"}
    """
    p = _coerce_params(cast(ParamsLike, model_params))

    bundle = compute_cpa_tcpa_tdb_twrp(
        da_lat=da_lat,
        da_lon=da_lon,
        da_radius_km=da_radius_km,
        trk_lat=track_lat,
        trk_lon=track_lon,
        speed_mps=speed_mps,
        heading_deg=heading_deg,
        weapon_range_km=(weapon_range_km or da_radius_km),
    )

    # --- normalization scales ---
    cpa_scale_km = float(p.get("cpa_scale_km", 20.0))
    tcpa_scale_s = float(p.get("tcpa_scale_s", 120.0))
    tdb_scale_km = float(p.get("tdb_scale_km", 30.0))
    twrp_scale_s = float(p.get("twrp_scale_s", 120.0))

    # Negative TCPA → past → normalize as ∞
    tcpa_norm = None if (
        bundle.tcpa_s is not None and bundle.tcpa_s < 0) else bundle.tcpa_s

    n_cpa = inv1(bundle.cpa_km, cpa_scale_km)
    n_tcpa = inv1(tcpa_norm, tcpa_scale_s)
    n_tdb = inv1(bundle.tdb_s, tdb_scale_km)
    n_twrp = inv1(bundle.twrp_s, twrp_scale_s)

    # --- weights ---
    w_cpa = float(p.get("w_cpa", 0.25))
    w_tcpa = float(p.get("w_tcpa", 0.25))
    w_tdb = float(p.get("w_tdb", 0.25))
    w_twrp = float(p.get("w_twrp", 0.25))
    clamp = bool(p.get("clamp_0_1", True))

    score = w_cpa * n_cpa + w_tcpa * n_tcpa + w_tdb * n_tdb + w_twrp * n_twrp
    if clamp:
        score = clamp01(score)

    return {
        "cpa_km": float(bundle.cpa_km),
        "tcpa_s": max(0.0, float(bundle.tcpa_s or 0.0)),
        "tdb_km": float(bundle.tdb_s),
        "twrp_s": float("inf") if bundle.twrp_s is None else float(bundle.twrp_s),
        "score": float(score),
    }


def score_components_to_threat(
    cpa_km: float,
    tcpa_s: Optional[float],
    tdb_km: float,
    twrp_s: Optional[float],
    params: ParamLike | ParamsLike | Mapping[str, Any] | ModelParams,
) -> float:
    """Wrapper to delegate to canonical scoring with type-flexible params."""
    return _score_components_to_threat(
        cpa_km=cpa_km,
        tcpa_s=tcpa_s,
        tdb_km=tdb_km,
        twrp_s=twrp_s,
        params=cast(ParamsLike, params),
    )


def compute_score_for_track(
    scenario: Scenario,
    da: DefendedAsset,
    track: Track,
    params: ParamLike | Mapping[str, Any] | ModelParams | ParamsLike,
    weapon_range_km: Optional[float] = None,
) -> ThreatScore:
    """
    Compute and persist the threat score for one track–DA pair.
    Uses normalized weights and scales, safe defaults, and full kinematic bundle.
    """
    # Coerce params (dict or ORM)
    p = _coerce_params(cast(ParamsLike, params))

    # Safe numeric access
    w_cpa = float(p.get("w_cpa", 0.0))
    w_tcpa = float(p.get("w_tcpa", 0.0))
    w_tdb = float(p.get("w_tdb", 0.0))
    w_twrp = float(p.get("w_twrp", 0.0))

    # Normalize zero weights
    if (w_cpa + w_tcpa + w_tdb + w_twrp) == 0.0:
        for k in ("w_cpa", "w_tcpa", "w_tdb", "w_twrp"):
            p[k] = 0.25

    # Compute all kinematic components
    bundle = compute_cpa_tcpa_tdb_twrp(
        da_lat=da.lat,
        da_lon=da.lon,
        da_radius_km=da.radius_km,
        trk_lat=track.lat,
        trk_lon=track.lon,
        speed_mps=track.speed_mps,
        heading_deg=track.heading_deg,
        weapon_range_km=weapon_range_km or da.radius_km,
    )

    # Compute final score
    score = score_components_to_threat(
        cpa_km=bundle.cpa_km,
        tcpa_s=bundle.tcpa_s,
        tdb_km=bundle.tdb_s,
        twrp_s=bundle.twrp_s,
        params=cast(ParamsLike, p),
    )

    # Persist ThreatScore row
    return ThreatScore.objects.create(
        scenario=scenario,
        track=track,
        da=da,
        cpa_km=bundle.cpa_km,
        tcpa_s=bundle.tcpa_s,
        tdb_km=bundle.tdb_s,
        twrp_s=bundle.twrp_s,
        score=score,
        computed_at=timezone.now(),
    )


def batch_compute_for_scenario(
    scenario_id: int,
    da_id: int,
    weapon_range_km: float | None = None,
) -> list[ThreatScore]:
    """
    Compute threat scores for all tracks in a given scenario/DA pair.
    Returns a list of ThreatScore objects.
    """
    start = time()
    scenario = Scenario.objects.get(id=scenario_id)
    da = DefendedAsset.objects.get(id=da_id)

    # Ensure parameters exist
    params, _ = ModelParams.objects.get_or_create(
        scenario=scenario,
        defaults=dict(
            w_cpa=0.25,
            w_tcpa=0.25,
            w_tdb=0.25,
            w_twrp=0.25,
            cpa_scale_km=20.0,
            tcpa_scale_s=120.0,
            tdb_scale_km=30.0,
            twrp_scale_s=120.0,
            clamp_0_1=True,
        ),
    )

    out: list[ThreatScore] = []
    for track in Track.objects.filter(scenario=scenario).iterator():
        out.append(
            compute_score_for_track(
                scenario=scenario,
                da=da,
                track=track,
                params=cast(ParamsLike, params),
                weapon_range_km=weapon_range_km,
            )
        )

    duration = round(time() - start, 3)
    print(f"[TEWA] Computed {len(out)} scores in {duration}s")
    return out


def calculate_scores_for_when(
    scenario: Scenario,
    when,
    das: list[DefendedAsset],
    method: str = "linear",
    weapon_range_km: float = 20.0,
) -> List[Dict]:
    """Pure compute (no DB writes), used by analytics or playback."""
    params_obj = (
        ModelParams.objects.filter(scenario=scenario).first()
        or ModelParams.objects.first()
    )
    if not params_obj:
        return []

    P = _coerce_params(cast(ParamsLike, params_obj))

    tracks = Track.objects.filter(scenario=scenario).only("id", "track_id")
    results: List[Dict] = []

    for tr in tracks:
        state = sampling.get_state(tr, when=when, method=method)
        if not state:
            continue

        lat, lon, spd, hdg = (
            state["lat"],
            state["lon"],
            state["speed_mps"],
            state["heading_deg"],
        )

        for da in das:
            bundle = compute_cpa_tcpa_tdb_twrp(
                da_lat=da.lat,
                da_lon=da.lon,
                da_radius_km=da.radius_km,
                trk_lat=lat,
                trk_lon=lon,
                speed_mps=spd,
                heading_deg=hdg,
                weapon_range_km=weapon_range_km or da.radius_km,
            )

            n_cpa = inv1(bundle.cpa_km, P.get("cpa_scale_km", 20.0))
            n_tcpa = inv1(
                bundle.tcpa_s if (
                    bundle.tcpa_s is None or bundle.tcpa_s >= 0) else float("inf"),
                P.get("tcpa_scale_s", 120.0),
            )
            n_tdb = inv1(bundle.tdb_s, P.get("tdb_scale_km", 30.0))
            n_twrp = inv1(
                bundle.twrp_s if (
                    bundle.twrp_s is None or bundle.twrp_s >= 0) else float("inf"),
                P.get("twrp_scale_s", 120.0),
            )

            score = (
                P.get("w_cpa", 0.25) * n_cpa
                + P.get("w_tcpa", 0.25) * n_tcpa
                + P.get("w_tdb", 0.25) * n_tdb
                + P.get("w_twrp", 0.25) * n_twrp
            )
            if P.get("clamp_0_1", True):
                score = clamp01(score)

            results.append(
                dict(
                    track_id=tr.track_id,
                    da_name=da.name,
                    score=round(float(score), 6),
                    components=dict(
                        dcpa=bundle.cpa_km,
                        tcpa=bundle.tcpa_s,
                        tdb=bundle.tdb_s,
                        twrp=bundle.twrp_s,
                        n_dcpa=n_cpa,
                        n_tcpa=n_tcpa,
                        n_tdb=n_tdb,
                        n_twrp=n_twrp,
                    ),
                    sampled_at=_iso(state["sampled_at"]),
                )
            )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
