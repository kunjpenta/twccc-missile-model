# tewa/services/score_breakdown_service.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.utils.dateparse import parse_datetime

# Existing domain compute (unchanged)
from tewa.services.score_breakdown import (
    get_score_breakdown as compute_breakdown_raw,
)

from ..models import DefendedAsset, Scenario, ThreatScore, Track

# ---------------------------
# Utilities
# ---------------------------


def _to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _latest_threatscore(
    scenario_id: int, da_id: int, track_pk: int, at_iso: Optional[str]
) -> Optional[ThreatScore]:
    qs = ThreatScore.objects.filter(
        scenario_id=scenario_id, da_id=da_id, track_id=track_pk
    )
    if at_iso:
        dt = parse_datetime(at_iso)
        if dt:
            qs = qs.filter(computed_at__lte=dt)
    return qs.order_by("-computed_at", "-id").first()


def _resolve_track_pk(track_identifier: str) -> Optional[int]:
    """
    Accept DB pk or public track_id string (latest row wins if duplicates).
    """
    try:
        return int(str(track_identifier))
    except Exception:
        pass

    tr = (
        Track.objects.filter(track_id=str(track_identifier))
        .order_by("-id")
        .first()
    )
    if not tr:
        return None
    return cast(Optional[int], getattr(tr, "pk", None))


def _ensure_legacy_flat_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add legacy top-level fields expected by older tests/UI:
      cpa_km, tcpa_s, tdb_km, twrp_s

    Source preference:
      1) payload["components"] (compute path)
      2) payload["metrics"] (new shape) — derive cpa_km from cpa_m, pass through times
    """
    # From components
    comps = payload.get("components") or {}
    if isinstance(comps, dict):
        if "cpa_km" in comps and payload.get("cpa_km") is None:
            payload["cpa_km"] = float(comps.get("cpa_km", 0.0))
        if "tdb_km" in comps and payload.get("tdb_km") is None:
            payload["tdb_km"] = float(comps.get("tdb_km", 0.0))
        if "tcpa_s" in comps and payload.get("tcpa_s") is None:
            payload["tcpa_s"] = float(comps.get("tcpa_s", 0.0))
        if "twrp_s" in comps and payload.get("twrp_s") is None:
            payload["twrp_s"] = float(comps.get("twrp_s", 0.0))

    # From metrics
    mets = payload.get("metrics") or {}
    if isinstance(mets, dict):
        if payload.get("cpa_km") is None and "cpa_m" in mets:
            payload["cpa_km"] = float(mets["cpa_m"]) / 1000.0
        if payload.get("tcpa_s") is None and "tcpa_s" in mets:
            payload["tcpa_s"] = float(mets["tcpa_s"])
        if payload.get("twrp_s") is None and "twrp_s" in mets:
            payload["twrp_s"] = float(mets["twrp_s"])
        # We intentionally do NOT synthesize tdb_km from tdb_s (unknown closure)
    return payload


# ---------------------------
# Public service
# ---------------------------

def get_score_breakdown(
    *,
    scenario_id: int,
    track_id: str,
    da_id: int,
    at_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Non-breaking wrapper:
      1) Validate Scenario/DA exist (404 semantics).
      2) Try existing compute (compute_breakdown_raw).
      3) On MultipleObjectsReturned or any compute hiccup, fall back to the latest ThreatScore row
         and shape the API (always including legacy flat fields).
    """
    # Validate existence
    try:
        Scenario.objects.only("id").get(pk=scenario_id)
    except Scenario.DoesNotExist as e:
        raise ObjectDoesNotExist(f"Scenario {scenario_id} not found") from e

    try:
        DefendedAsset.objects.only("id").get(pk=da_id)
    except DefendedAsset.DoesNotExist as e:
        raise ObjectDoesNotExist(f"Defended Asset {da_id} not found") from e

    # --- Compute path (preferred; leaves old code untouched) ---
    try:
        raw = compute_breakdown_raw(
            scenario_id=scenario_id,
            track_id=track_id,
            da_id=da_id,
            persist=True,
            weapon_range_km=10.0,
        )
        raw = cast(Dict[str, Any], raw)

        # Normalize timestamp to ISO UTC if a datetime leaked through
        # Normalize timestamp to ISO UTC if a datetime leaked through
        comp_at = raw.get("computed_at")
        if isinstance(comp_at, datetime):
            raw["computed_at"] = _to_utc_iso(comp_at)

        # Ensure legacy fields are present for backward-compat tests/UI
        raw.setdefault("cpa_km", None)
        raw.setdefault("tcpa_s", None)
        raw.setdefault("tdb_km", None)
        raw.setdefault("twrp_s", None)
        raw = _ensure_legacy_flat_fields(raw)

        # >>> NEW: set total_score (and score if missing) from best available source <<<
        score_val = raw.get("score")
        if score_val is None:
            score_val = raw.get("final_score")

        if score_val is None:
            # Last resort: read latest ThreatScore row for this key and use its .score
            track_pk = _resolve_track_pk(track_id)
            if track_pk is not None:
                ts_latest = _latest_threatscore(
                    scenario_id, da_id, track_pk, at_iso)
                if ts_latest and ts_latest.score is not None:
                    score_val = float(ts_latest.score)

        if score_val is not None:
            # ensure both fields are present for compatibility
            raw["score"] = float(score_val)
            raw["total_score"] = float(score_val)
        else:
            # keep a None value explicitly to satisfy serializer shape
            raw.setdefault("total_score", None)

        return raw

    except MultipleObjectsReturned:
        # duplicate TS rows in old compute; fall back to deterministic latest TS row
        pass
    except Exception:
        # any compute hiccup: still try to produce a valid response from stored rows
        pass

    # --- Fallback: latest ThreatScore timeseries row ---
    track_pk = _resolve_track_pk(track_id)
    if track_pk is None:
        raise ObjectDoesNotExist(f"Track '{track_id}' not found")

    ts = _latest_threatscore(scenario_id, da_id, track_pk, at_iso)
    if not ts:
        raise ObjectDoesNotExist(
            f"No ThreatScore found for scenario={scenario_id}, da={da_id}, track={track_id}"
        )

    # Build response (units from your model: cpa_km, tdb_km, tcpa_s, twrp_s)
    cpa_km = _f(ts.cpa_km)
    tcpa_s = _f(ts.tcpa_s)
    tdb_km = _f(ts.tdb_km)
    twrp_s = _f(ts.twrp_s)
    score = _f(ts.score)

    # Also provide new metrics block (meters/seconds), keeping UI contract
    cpa_m = cpa_km * 1000.0
    # Provide a conservative proxy for tdb_s if seconds are not stored
    nominal_closure_mps = 250.0  # ≈ 900 km/h
    tdb_s = (tdb_km * 1000.0) / \
        nominal_closure_mps if nominal_closure_mps > 0 else 0.0

    computed_at_iso = _to_utc_iso(ts.computed_at or datetime.now(timezone.utc))

    resp: Dict[str, Any] = {
        "scenario_id": scenario_id,
        "track_id": track_id,
        "da_id": da_id,
        "computed_at": computed_at_iso,
        "metrics": {
            "cpa_m": cpa_m,
            "tcpa_s": tcpa_s,
            "tdb_s": tdb_s,
            "twrp_s": twrp_s,
        },
        "normalized": {"cpa": 0.0, "tcpa": 0.0, "tdb": 0.0, "twrp": 0.0},
        "weights": {"cpa": 0.0, "tcpa": 0.0, "tdb": 0.0, "twrp": 0.0},
        "contributions": {"cpa": 0.0, "tcpa": 0.0, "tdb": 0.0, "twrp": 0.0},
        "score": score,
        "params": {},
        "explain": [
            "Lower CPA → higher normalized threat (inverted scale).",
            "Shorter TCPA → higher immediacy risk.",
            "TDB gauges time to DA boundary penetration (proxy used if seconds not available).",
            "TWRP indicates time to weapon release window.",
        ],
    }

    # Explicitly provide legacy flat fields for backward compatibility
    resp["cpa_km"] = cpa_km
    resp["tcpa_s"] = tcpa_s
    resp["tdb_km"] = tdb_km
    resp["twrp_s"] = twrp_s

    # (Optional) run the helper too, in case future compute adds components/metrics variants
    resp = _ensure_legacy_flat_fields(resp)

    return resp
