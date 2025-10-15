# tewa/api/views.py — keeps old import path stable
# keep near the top with other imports
from __future__ import annotations

import csv
import datetime as dt
from typing import List, Optional, cast

from django.http import HttpResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import render
from django.utils.http import http_date
from rest_framework import permissions, status  # single import is enough
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from tewa.models import ModelParams, Scenario
from tewa.services.charting import render_score_history_png
from tewa.services.export_csv import iter_rows_for_threat_board
from tewa.services.score_history import get_score_series

from .serializers import ScenarioParamsSerializer, ScoreBreakdownSerializer
from .views_compute import (
    calculate_scores,
    compute_at,
    compute_now,
    ranking,
    upload_tracks,  # noqa: F401
)

# read / viewsets / simple endpoints
from .views_read import (
    DefendedAssetViewSet,
    ScenarioViewSet,
    ThreatScoreViewSet,
    TrackSampleViewSet,
    TrackViewSet,
    da_list_api,
    root,
    scenarios,
    score,
    track_detail,
)

__all__ = [
    # compute/analytics
    "compute_now", "compute_at", "ranking", "calculate_scores", "upload_tracks", "score_breakdown",
    # read/viewsets
    "root", "ScenarioViewSet", "TrackViewSet", "TrackSampleViewSet", "ThreatScoreViewSet",
    "DefendedAssetViewSet", "scenarios", "score", "da_list_api", "track_detail",
]

from typing import Any, Dict

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from ..services.score_breakdown_service import get_score_breakdown
from .serializers import ScoreBreakdownSerializer


@api_view(["GET"])
def score_breakdown(request: Request) -> Response:
    """
    GET /api/tewa/score-breakdown?scenario_id=1&track_id=TGT001&da_id=3[&at=2025-10-14T10:02:00Z]
    Returns the Task 21 score-breakdown JSON (with legacy flat fields preserved).
    """
    qp = request.query_params
    scenario_id = qp.get("scenario_id")
    track_id = qp.get("track_id")
    da_id = qp.get("da_id")
    at = qp.get("at")

    # 422 — missing required params
    missing = [k for k, v in (("scenario_id", scenario_id),
                              ("track_id", track_id), ("da_id", da_id)) if not v]
    if missing:
        return Response(
            {"detail": f"Missing required params: {', '.join(missing)}"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # 422 — invalid integer types
    try:
        scenario_id_int = int(scenario_id)  # type: ignore[arg-type]
        da_id_int = int(da_id)              # type: ignore[arg-type]
    except (TypeError, ValueError):
        return Response(
            {"detail": "scenario_id and da_id must be integers"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        data: Dict[str, Any] = get_score_breakdown(
            scenario_id=scenario_id_int,
            track_id=str(track_id),
            da_id=da_id_int,
            at_iso=at,
        )
    except ValueError as ve:
        # 400 — bad 'at' format
        return Response({"detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist as dne:
        # 404 — not found for given IDs/time
        return Response({"detail": str(dne)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # 500 — unexpected internal error
        return Response({"detail": f"Internal error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Normalize legacy alias for older tests/UI: total_score mirrors score/final_score
    if data.get("total_score") is None:
        fallback_score = data.get("score", data.get("final_score"))
        if fallback_score is not None:
            data["total_score"] = fallback_score

    # Enforce response shape via serializer (passes through optional legacy fields)
    serializer = ScoreBreakdownSerializer(instance=data)
    return Response(serializer.data, status=status.HTTP_200_OK)


# --- DEBUG PAGE (read-only UI) ---


def score_breakdown_debug(request):
    return render(request, "debug/score_breakdown_demo.html")


# tewa/api/views.py  (append)


class Echo:
    """File-like wrapper for csv.writer streaming."""

    def write(self, value: str) -> str:
        return value


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def export_threat_board_csv(request):
    # scenario_id (required)
    try:
        scenario_id = int(request.GET.get("scenario_id")
                          )  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return HttpResponseBadRequest("scenario_id is required and must be int")

    # da_id (optional)
    da_id_q = request.GET.get("da_id")
    da_id: Optional[int] = int(da_id_q) if da_id_q not in (None, "",) else None

    # at (optional ISO-8601 UTC string; we pass through to providers)
    at_iso = request.GET.get("at")

    # top_n (optional)
    top_n_q = request.GET.get("top_n")
    try:
        top_n: Optional[int] = int(top_n_q) if top_n_q else None
    except ValueError:
        return HttpResponseBadRequest("top_n must be int")

    # fields (optional CSV list)
    fields_param = request.GET.get("fields")
    fields: Optional[List[str]] = (
        [f.strip() for f in fields_param.split(",")] if fields_param else None
    )

    # filename
    # Prefer timestamp from 'at' if provided/valid; else UTC now
    ts = None
    try:
        # safe parse limited to formatting; don't import dateutil
        ts = dt.datetime.fromisoformat(at_iso.replace(
            "Z", "+00:00")) if at_iso else None  # type: ignore[arg-type]
    except Exception:
        ts = None
    stamp = (ts or dt.datetime.utcnow()).strftime("%Y-%m-%dT%H-%M-%SZ")

    fname = f"threat_board_s{scenario_id}"
    if da_id is not None:
        fname += f"_da{da_id}"
    fname += f"_{stamp}.csv"

    pseudo = Echo()
    writer = csv.writer(pseudo)

    def generate():
        for row in iter_rows_for_threat_board(
            scenario_id=scenario_id,
            da_id=da_id,
            at_iso=at_iso,
            top_n=top_n,
            fields=fields,
        ):
            yield writer.writerow(row)

    resp = StreamingHttpResponse(generate(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    return resp


# tewa/api/views.py


class ScenarioParamsView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_object(self, scenario_id: int) -> ModelParams:
        scenario = Scenario.objects.get(pk=scenario_id)
        params, _ = ModelParams.objects.get_or_create(scenario=scenario)
        return params

    def get(self, request, scenario_id: int):
        params = self.get_object(scenario_id)
        return Response(ScenarioParamsSerializer(params).data)

    def patch(self, request, scenario_id: int):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        params = self.get_object(scenario_id)

        serializer = cast(
            ScenarioParamsSerializer,
            ScenarioParamsSerializer(params, data=request.data, partial=True)
        )
        serializer.is_valid(raise_exception=True)

        inst = serializer.save()
        if hasattr(inst, "updated_by"):
            setattr(inst, "updated_by", request.user)
            inst.save(update_fields=["updated_by"])

        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def score_history_png_view(request):
    # required params
    try:
        scenario_id = int(request.GET["scenario_id"])
        da_id = int(request.GET["da_id"])
        track_id = request.GET["track_id"]
    except KeyError:
        return HttpResponseBadRequest("scenario_id, da_id, track_id are required")
    except ValueError:
        return HttpResponseBadRequest("IDs must be integers")

    # optional params
    dt_from = request.GET.get("from")
    dt_to = request.GET.get("to")
    width = int(request.GET.get("width", 800))
    height = int(request.GET.get("height", 300))
    smooth_q = request.GET.get("smooth")
    smooth = int(smooth_q) if smooth_q else None

    # fetch series
    series = get_score_series(scenario_id, da_id, track_id, dt_from, dt_to)
    if not series:
        return Response({"detail": "No score history found"}, status=status.HTTP_404_NOT_FOUND)

    # render PNG
    png = render_score_history_png(
        series, width=width, height=height, smooth=smooth)

    resp = HttpResponse(png, content_type="image/png")
    last_ts = series[-1][0]
    if last_ts:
        resp["Last-Modified"] = http_date(last_ts.timestamp())
    resp["Cache-Control"] = "private, max-age=60"
    return resp
