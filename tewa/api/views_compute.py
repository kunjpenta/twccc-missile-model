# tewa/api/views_compute.py
from __future__ import annotations

import uuid
from datetime import timedelta
from datetime import timezone as dt_timezone
from inspect import signature
from typing import Any, Dict, List, Mapping, Optional, cast

from django.db.models import F, OuterRef, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tewa.api.query_schemas import RankingQuerySerializer
from tewa.api.view_utils import bad_request, iso_utc, iso_utc_now
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track
from tewa.services.csv_import import import_csv
from tewa.services.engine import compute_scores_at_timestamp
from tewa.services.ranking import rank_threats
from tewa.services.threat_compute import calculate_scores_for_when

# ---------- helpers to keep the type-checker happy ----------


def _as_mapping(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, Mapping):
        return cast(Mapping[str, Any], obj)
    return cast(Mapping[str, Any], {})


def _get_str(m: Mapping[str, Any], key: str) -> str:
    v = m.get(key, "")
    if isinstance(v, str):
        return v
    return "" if v is None else str(v)


def _get_int(m: Mapping[str, Any], key: str) -> Optional[int]:
    s = _get_str(m, key).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _supports_batch_id() -> bool:
    try:
        return "batch_id" in signature(compute_scores_at_timestamp).parameters
    except Exception:
        return False


# ------------------------------ endpoints ------------------------------

@api_view(["POST"])
def compute_now(request):
    body = _as_mapping(getattr(request, "data", {}))
    scenario_id_opt = _get_int(body, "scenario_id")
    method = _get_str(body, "method") or "linear"

    if scenario_id_opt is None:
        return bad_request("scenario_id is required")
    scenario_id: int = scenario_id_opt

    # ensure plain str (some stubs mark helpers as Optional[str])
    when_iso: str = iso_utc_now() or iso_utc(
        timezone.now()) or timezone.now().isoformat()

    kwargs: Dict[str, Any] = {
        "scenario_id": scenario_id, "when_iso": when_iso, "method": method}
    batch_id: Optional[str] = None
    if _supports_batch_id():
        batch_id = str(uuid.uuid4())
        kwargs["batch_id"] = batch_id

    try:
        cast(Any, compute_scores_at_timestamp)(**kwargs)
    except Exception as e:
        return Response({"detail": f"Compute failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {"status": "ok", "scenario_id": scenario_id, "method": method,
            "computed_at": when_iso, "batch_id": batch_id},
        status=200,
    )


@api_view(["POST"])
def compute_at(request):
    body = _as_mapping(getattr(request, "data", {}))

    scenario_id_opt = _get_int(body, "scenario_id")
    if scenario_id_opt is None:
        return Response({"detail": "scenario_id is required"}, status=400)
    scenario_id: int = scenario_id_opt

    when_str = _get_str(body, "when")
    when = parse_datetime(when_str) if when_str else None
    if when is None:
        return Response({"detail": "Invalid 'when' datetime"}, status=400)
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    method = _get_str(body, "method") or "linear"

    # da_ids handling
    da_ids_val = body.get("da_ids")
    da_ids: Optional[List[int]]
    if da_ids_val in (None, "", []):
        da_ids = None
    elif isinstance(da_ids_val, list):
        try:
            da_ids = [int(x) for x in da_ids_val]
        except (TypeError, ValueError):
            return Response({"detail": "da_ids must be a list of integers"}, status=400)
    else:
        return Response({"detail": "da_ids must be a list of integers or null"}, status=400)

    # weapon_range_km handling
    wr_raw = body.get("weapon_range_km", None)
    if wr_raw in (None, ""):
        weapon_range_km: Optional[float] = None
    else:
        try:
            weapon_range_km = float(wr_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return Response({"detail": "weapon_range_km must be a number"}, status=400)

    when_iso_str: str = iso_utc(when) or when.isoformat()

    kwargs: Dict[str, Any] = {
        "scenario_id": scenario_id,
        "when_iso": when_iso_str,
        "method": method,
        "da_ids": da_ids,
        "weapon_range_km": weapon_range_km,
    }
    batch_id: Optional[str] = None
    if _supports_batch_id():
        batch_id = str(uuid.uuid4())
        kwargs["batch_id"] = batch_id

    call_started = timezone.now()
    try:
        cast(Any, compute_scores_at_timestamp)(**kwargs)
    except Exception as e:
        return Response({"detail": f"Compute failed: {e}"}, status=500)

    # Collect rows written by this call
    has_batch_field = any(getattr(f, "name", "") ==
                          "batch_id" for f in ThreatScore._meta.get_fields())
    if batch_id and has_batch_field:
        qs = (
            ThreatScore.objects.filter(
                scenario_id=scenario_id, batch_id=batch_id)
            .select_related("track", "da")
            .order_by("-score")
        )
    else:
        window_start = call_started - timedelta(seconds=2)
        qs = (
            ThreatScore.objects.filter(
                scenario_id=scenario_id, computed_at__gte=window_start)
            .select_related("track", "da")
            .order_by("-score")
        )
        if da_ids:
            qs = qs.filter(da_id__in=da_ids)  # type: ignore[attr-defined]

    scores_simple = [
        {
            "track_id": getattr(ts.track, "track_id", None),
            # keep checker happy; Django model has da_id DB field even if stubs don't
            "da_id": cast(Any, ts).da_id if hasattr(ts, "da_id") else (ts.da.pk if getattr(ts, "da", None) else None),
            "da_name": getattr(ts.da, "name", None),
            "score": float(ts.score) if ts.score is not None else None,
            "computed_at": iso_utc(ts.computed_at),
        }
        for ts in qs
    ]

    return Response(
        {
            "status": "ok",
            "scenario_id": scenario_id,
            "when": when_iso_str,
            "method": method,
            "count": len(scores_simple),
            "scores": scores_simple,
            "threats": scores_simple,
            "batch_id": batch_id,
        },
        status=200,
    )


@api_view(["GET"])
def ranking(request):
    params = _as_mapping(getattr(request, "query_params", {}))
    q = RankingQuerySerializer(data=params)
    q.is_valid(raise_exception=True)
    vd = cast(Dict[str, Any], q.validated_data)

    sid: int = cast(int, vd["scenario_id"])
    top_n: int = cast(int, vd.get("top_n", 10))

    try:
        results = rank_threats(
            scenario_id=sid, da_id=vd.get("da_id"), top_n=top_n)
    except Exception as e:
        return Response({"detail": f"Failed to rank: {e}"}, status=500)

    return Response({"scenario_id": sid, "threats": results})


@require_POST
@csrf_exempt  # prefer proper auth/CSRF in prod
def calculate_scores(request):
    # DRF already parses JSON; avoid dict(bytes) footguns
    body = _as_mapping(getattr(request, "data", {}))

    scenario_id_opt = _get_int(body, "scenario_id")
    when_str = _get_str(body, "when")

    if scenario_id_opt is None:
        return Response({"detail": "scenario_id is required"}, status=400)
    if not when_str:
        return Response({"detail": "Invalid 'when' datetime"}, status=400)

    scenario_id: int = scenario_id_opt

    when = parse_datetime(when_str)
    if when is None:
        return Response({"detail": "Invalid 'when' datetime"}, status=400)
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    try:
        scenario = Scenario.objects.get(id=scenario_id)
    except Scenario.DoesNotExist:
        return Response({"detail": f"Scenario {scenario_id} not found"}, status=404)

    da_ids_val = body.get("da_ids") or []
    das = list(DefendedAsset.objects.filter(id__in=da_ids_val)) if isinstance(
        da_ids_val, list) else list(DefendedAsset.objects.all())
    method = _get_str(body, "method") or "latest"

    wr = body.get("weapon_range_km", 20)
    try:
        weapon_range_km = float(wr)  # type: ignore[arg-type]
    except Exception:
        weapon_range_km = 20.0

    try:
        threats = calculate_scores_for_when(
            scenario=scenario, when=when, das=das, method=method, weapon_range_km=weapon_range_km
        )
    except Exception as e:
        return Response({"detail": f"Failed to compute: {e}"}, status=500)

    return Response(
        {"scenario_id": scenario.pk, "computed_at": (
            iso_utc_now() or timezone.now().isoformat()), "threats": threats}
    )


@require_POST
@csrf_exempt  # prefer proper auth/CSRF in prod
def upload_tracks(request):
    files_map = _as_mapping(getattr(request, "FILES", {}))
    upfile = files_map.get("file")
    if not upfile:
        return Response({"detail": "No file provided"}, status=400)
    try:
        # type: ignore[attr-defined]
        content = upfile.read().decode("utf-8", errors="replace")
        result = import_csv(content)
        return Response(result)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)


@api_view(["GET"])
def score_breakdown(request):
    """
    GET query:
      scenario_id: int (required)
      da_id: int (required)
      track_id: str|int (optional)

    If track_id is provided -> return the latest ThreatScore for that track.
    If omitted -> return latest ThreatScore per track for the DA.
    """
    params = _as_mapping(getattr(request, "query_params", {}))

    sid_opt = _get_int(params, "scenario_id")
    da_opt = _get_int(params, "da_id")
    if sid_opt is None or da_opt is None:
        return Response({"detail": "scenario_id and da_id are required integers"}, status=400)
    scenario_id: int = sid_opt
    da_id: int = da_opt

    track_raw = _get_str(params, "track_id").strip()
    track_pk: Optional[int] = None
    track_public_id: Optional[str] = None

    if track_raw:
        if track_raw.isdigit():
            try:
                t = Track.objects.only("id", "track_id").get(pk=int(track_raw))
                track_pk = int(t.pk)
                track_public_id = t.track_id
            except Track.DoesNotExist:
                return Response({"detail": f"Track pk={track_raw} not found"}, status=404)
        else:
            track_public_id = track_raw

    base = ThreatScore.objects.filter(scenario_id=scenario_id, da_id=da_id)

    # Specific track case
    if track_pk is not None or track_public_id:
        qs = base.select_related("track", "da").order_by("-computed_at")
        if track_pk is not None:
            qs = qs.filter(track_id=track_pk)
        else:
            qs = qs.filter(track__track_id=track_public_id)

        row = qs.first()
        if not row:
            return Response({"detail": "No scores found"}, status=404)

        return Response(
            {
                "scenario_id": scenario_id,
                "da_id": da_id,
                "track_id": getattr(row.track, "track_id", None),
                "cpa_km": float(row.cpa_km) if row.cpa_km is not None else None,
                "tcpa_s": float(row.tcpa_s) if row.tcpa_s is not None else None,
                "tdb_km": float(row.tdb_km) if row.tdb_km is not None else None,
                "twrp_s": float(row.twrp_s) if row.twrp_s is not None else None,
                "total_score": float(row.score) if row.score is not None else None,
                "score": float(row.score) if row.score is not None else None,
                "computed_at": iso_utc(row.computed_at),
            },
            status=200,
        )

    # Latest per track for this DA
    sub = Subquery(
        ThreatScore.objects
        .filter(scenario_id=scenario_id, da_id=da_id, track_id=OuterRef("track_id"))
        .order_by("-computed_at", "-id")
        .values("computed_at")[:1]
    )
    rows = (
        base.annotate(latest_t=sub)
        .filter(computed_at=F("latest_t"))
        .select_related("track", "da")
        .order_by("-score")
    )

    results: List[Dict[str, Any]] = [
        {
            "scenario_id": scenario_id,
            "da_id": da_id,
            "track_id": getattr(r.track, "track_id", None),
            "cpa_km": float(r.cpa_km) if r.cpa_km is not None else None,
            "tcpa_s": float(r.tcpa_s) if r.tcpa_s is not None else None,
            "tdb_km": float(r.tdb_km) if r.tdb_km is not None else None,
            "twrp_s": float(r.twrp_s) if r.twrp_s is not None else None,
            "score": float(r.score) if r.score is not None else None,
            "computed_at": iso_utc(r.computed_at),
        }
        for r in rows
    ]

    return Response({"results": results, "count": len(results)}, status=200)
