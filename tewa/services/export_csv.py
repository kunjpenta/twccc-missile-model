# tewa/services/export_csv.py
from __future__ import annotations
from django.db.models import F, Max, OuterRef, Subquery

from typing import Any, Dict, Iterable, List, Optional, cast  # add cast

# Prefer a proper ranked board provider if you have one:
# - include_components/norms/weights/contribs MUST be honored when True.
try:
    from .ranking import get_ranked_threats  # type: ignore
except Exception:
    get_ranked_threats = None  # Fallback below


from ..models import ThreatScore

DEFAULT_FIELDS: List[str] = [
    "scenario_id", "da_id", "track_id", "computed_at", "score",
    "cpa_m", "tcpa_s", "tdb_s", "twrp_s",
    "norm_cpa", "norm_tcpa", "norm_tdb", "norm_twrp",
    "w_cpa", "w_tcpa", "w_tdb", "w_twrp",
    "contrib_cpa", "contrib_tcpa", "contrib_tdb", "contrib_twrp",
]

# tewa/services/export_csv.py


# ... keep existing imports ...


def _fallback_board_rows(
    scenario_id: int,
    da_id: Optional[int],
    at_iso: Optional[str],
    top_n: Optional[int],
) -> List[Dict[str, Any]]:
    """
    Fallback when ranking service is unavailable.
    Returns one row per (da_id, track_id): the latest ThreatScore (<= at if given).
    Norms/weights/contribs are zeros (can’t reconstruct without compute).
    """
    # Base set restricted by scenario (+ optional DA)
    base = ThreatScore.objects.filter(scenario_id=scenario_id)
    if da_id is not None:
        base = base.filter(da_id=da_id)

    # Subquery: latest row id per (da, track) ≤ at (if provided)
    latest_row_sq = ThreatScore.objects.filter(
        scenario_id=scenario_id,
        da_id=OuterRef("da_id"),
        track_id=OuterRef("track_id"),
    )
    if da_id is not None:
        latest_row_sq = latest_row_sq.filter(da_id=da_id)
    if at_iso:
        latest_row_sq = latest_row_sq.filter(computed_at__lte=at_iso)

    latest_row_sq = latest_row_sq.order_by(
        "-computed_at", "-id").values("id")[:1]

    # Collect those latest ids for each pair present in `base`
    pair_latest = (
        base.values("da_id", "track_id")
            .annotate(latest_id=Subquery(latest_row_sq))
            .values_list("latest_id", flat=True)
    )

    rows_qs = ThreatScore.objects.filter(id__in=pair_latest).order_by(
        F("score").desc(nulls_last=True), "-computed_at", "-id"
    )
    if top_n:
        rows_qs = rows_qs[:top_n]

    qs_vals = rows_qs.values(
        "scenario_id", "da_id", "track_id", "computed_at", "score",
        "cpa_km", "tcpa_s", "tdb_km", "twrp_s",
    )

    rows: List[Dict[str, Any]] = []
    for r in qs_vals:
        cpa_m = float(r.get("cpa_km") or 0.0) * 1000.0
        tcpa_s = float(r.get("tcpa_s") or 0.0)
        # Keep the TDB proxy (km → s) consistent with Task 21:
        tdb_s = (float(r.get("tdb_km") or 0.0) * 1000.0) / 250.0
        twrp_s = r.get("twrp_s")  # may be None; leave blank in CSV

        rows.append({
            "scenario_id": r["scenario_id"],
            "da_id": r["da_id"],
            "track_id": str(r["track_id"]),
            "computed_at": r["computed_at"],
            "score": float(r.get("score") or 0.0),
            "cpa_m": cpa_m,
            "tcpa_s": tcpa_s,
            "tdb_s": tdb_s,
            "twrp_s": twrp_s if twrp_s is not None else None,
            "normalized": {"cpa": 0.0, "tcpa": 0.0, "tdb": 0.0, "twrp": 0.0},
            "weights": {"cpa": 0.0, "tcpa": 0.0, "tdb": 0.0, "twrp": 0.0},
            "contributions": {"cpa": 0.0, "tcpa": 0.0, "tdb": 0.0, "twrp": 0.0},
        })
    return rows


def _ensure_rowmap(it: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize varying shapes from ranking/compute into a flat row mapping."""
    metrics = it.get("metrics") or {}
    normalized = it.get("normalized") or {}
    weights = it.get("weights") or {}
    contrib = it.get("contributions") or {}

    # Allow both integer or string track ids; always emit as string
    track = it.get("track_id")
    track_str = str(track)

    return {
        "scenario_id": it["scenario_id"],
        "da_id": it.get("da_id"),
        "track_id": track_str,
        "computed_at": it.get("computed_at"),
        "score": it.get("score"),
        "cpa_m": metrics.get("cpa_m"),
        "tcpa_s": metrics.get("tcpa_s"),
        "tdb_s": metrics.get("tdb_s"),
        "twrp_s": metrics.get("twrp_s"),
        "norm_cpa": normalized.get("cpa", 0.0),
        "norm_tcpa": normalized.get("tcpa", 0.0),
        "norm_tdb": normalized.get("tdb", 0.0),
        "norm_twrp": normalized.get("twrp", 0.0),
        "w_cpa": weights.get("cpa", 0.0),
        "w_tcpa": weights.get("tcpa", 0.0),
        "w_tdb": weights.get("tdb", 0.0),
        "w_twrp": weights.get("twrp", 0.0),
        "contrib_cpa": contrib.get("cpa", 0.0),
        "contrib_tcpa": contrib.get("tcpa", 0.0),
        "contrib_tdb": contrib.get("tdb", 0.0),
        "contrib_twrp": contrib.get("twrp", 0.0),
    }


def iter_rows_for_threat_board(
    scenario_id: int,
    da_id: Optional[int] = None,
    at_iso: Optional[str] = None,
    top_n: Optional[int] = None,
    fields: Optional[List[str]] = None,
) -> Iterable[List[str]]:
    cols = fields or DEFAULT_FIELDS
    yield cols  # header

    # Fetch items (prefer ranking provider). Accept any iterable of dict-like rows.
    if callable(get_ranked_threats):
        raw = get_ranked_threats(
            scenario_id=scenario_id,
            da_id=da_id,
            at_iso=at_iso,
            top_n=top_n,
            include_components=True,
            include_norms=True,
            include_weights=True,
            include_contribs=True,
        )
        # Ensure it's something we can iterate multiple times if needed
        items = list(raw)  # type: ignore[misc]
    else:
        items = _fallback_board_rows(scenario_id, da_id, at_iso, top_n)

    for it in items:
        rowmap = _ensure_rowmap(cast(Dict[str, Any], it))
        yield ["" if rowmap.get(f) is None else str(rowmap.get(f)) for f in cols]
