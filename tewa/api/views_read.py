# tewa/api/views_read.py
from __future__ import annotations

from typing import Any, Dict

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tewa.api.query_schemas import ScoreListQuerySerializer
from tewa.api.serializers import (
    DefendedAssetSerializer,
    ScenarioSerializer,
    ThreatScoreSerializer,
    TrackSampleSerializer,
    TrackSerializer,
)
from tewa.api.view_utils import iso_utc
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample


@api_view(["GET"])
def root(_):
    return Response({
        "name": "TEWA API",
        "endpoints": [
            "/api/tewa/scenarios/",
            "/api/tewa/da/",
            "/api/tewa/score/",
            "/api/tewa/ranking/",
            "/api/tewa/compute_now/",
            "/api/tewa/compute_at",
            "/api/tewa/upload_tracks/",
            "/api/tewa/calculate_scores/",
            "/api/tewa/score-breakdown",
        ]
    })


class ScenarioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Scenario.objects.all()
    serializer_class = ScenarioSerializer


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer


class TrackSampleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrackSample.objects.all()
    serializer_class = TrackSampleSerializer


class ThreatScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ThreatScore.objects.select_related("track", "da").all()
    serializer_class = ThreatScoreSerializer

    def list(self, request, *args, **kwargs):
        q = ScoreListQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        vd = q.validated_data
        qs = self.get_queryset()
        if vd.get("scenario_id"):
            qs = qs.filter(scenario_id=vd["scenario_id"])
        if vd.get("da_id"):
            qs = qs.filter(da_id=vd["da_id"])
        qs = qs.order_by(vd["ordering"])
        qs = qs.only("id", "scenario_id", "da_id",
                     "track_id", "score", "computed_at")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DefendedAssetViewSet(viewsets.ModelViewSet):
    queryset = DefendedAsset.objects.all()
    serializer_class = DefendedAssetSerializer


@api_view(["GET"])
def scenarios(_request):
    qs = Scenario.objects.all().order_by("id").only(
        "id", "name", "start_time", "end_time")
    return Response(ScenarioSerializer(qs, many=True).data)


# tewa/api/views_read.py (or wherever your score alias lives)


@api_view(["GET"])
def score(request, *args, **kwargs):
    """
    Alias for router-backed ThreatScore list.
    """
    view = ThreatScoreViewSet.as_view({"get": "list"})
    # Important: pass the underlying Django HttpRequest
    return view(request._request, *args, **kwargs)


@api_view(['GET', 'POST'])
def da_list_api(request):
    if request.method == 'GET':
        das = DefendedAsset.objects.all().order_by(
            'name').only('id', 'name', 'lat', 'lon')
        return Response(DefendedAssetSerializer(das, many=True).data)
    serializer = DefendedAssetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


def _iso_utc(dt):
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@api_view(['GET'])
def track_detail(request):
    """
    GET /api/tewa/tracks/detail/?track_id=T1&scenario_id=1
    """
    track_id = request.query_params.get("track_id")
    scenario_id = request.query_params.get("scenario_id")

    if not track_id or not scenario_id:
        return Response({"detail": "track_id and scenario_id are required"}, status=400)

    track = (
        Track.objects
        .filter(track_id=track_id, scenario_id=scenario_id)
        .order_by('-id')
        .first()
    )
    if track is None:
        return Response({"detail": "Track not found"}, status=404)

    # Make a mutable copy so type checkers are happy
    base: Dict[str, Any] = dict(TrackSerializer(track).data)

    # Query ThreatScore explicitly instead of using track.threatscore_set
    rows = (
        ThreatScore.objects
        .filter(track=track)
        .select_related("da")
        .only("score", "computed_at", "da_id", "da__name")
        .values("da__name", "score", "computed_at")
    )

    base["threat_scores"] = [
        {
            "da_name": r["da__name"],
            "score": float(r["score"]) if r["score"] is not None else None,
            "computed_at": _iso_utc(r["computed_at"]) if r["computed_at"] else None,
        }
        for r in rows
    ]
    return Response(base)
