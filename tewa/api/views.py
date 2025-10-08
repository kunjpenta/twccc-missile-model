# tewa/api/views.py

import json
from datetime import timedelta
from datetime import timezone as dt_timezone
from typing import List, Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tewa.api.serializers import (
    DefendedAssetSerializer,
    ScenarioSerializer,
    ThreatScoreSerializer,
    TrackSampleSerializer,
    TrackSerializer,
)
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample
from tewa.services import csv_import
from tewa.services.csv_import import import_csv
from tewa.services.engine import compute_scores_at_timestamp
from tewa.services.ranking import rank_threats
from tewa.services.threat_compute import calculate_scores_for_when

from .serializers import DefendedAssetSerializer, TrackSerializer

# from tewa.tasks import periodic_compute_threats  # optional queue

# ------------------------------
# Helpers
# ------------------------------


def _iso_utc_now() -> str:
    """Return current time in strict Zulu ISO-8601."""
    return timezone.now().astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_utc(dt):
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def _bad_request(msg: str) -> Response:
    # Frontend error normalizer checks for `detail` or `message`
    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------
# Root
# ------------------------------


def root(_):
    return JsonResponse({
        "name": "TEWA API",
        "endpoints": [
            "/api/tewa/scenarios/",
            "/api/tewa/da/",
            "/api/tewa/score/",
            "/api/tewa/ranking/",
            "/api/tewa/compute_now/",
            "/api/tewa/compute_at/",
            "/api/tewa/upload_tracks/",
            "/api/tewa/calculate_scores/",
        ]
    })

# ------------------------------
# Read-Only ViewSets
# ------------------------------


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
    """
    GET /score/?scenario_id=&da_id=&ordering=-score
    """
    queryset = ThreatScore.objects.all()
    serializer_class = ThreatScoreSerializer

    def list(self, request, *args, **kwargs):
        scenario_id = request.query_params.get("scenario_id")
        da_id = request.query_params.get("da_id")
        ordering = request.query_params.get("ordering", "-score")

        qs = self.get_queryset()
        if scenario_id:
            qs = qs.filter(scenario_id=scenario_id)
        if da_id:
            qs = qs.filter(da_id=da_id)
        if ordering:
            qs = qs.order_by(ordering)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DefendedAssetViewSet(viewsets.ModelViewSet):
    """Full CRUD for DAs."""
    queryset = DefendedAsset.objects.all()
    serializer_class = DefendedAssetSerializer

# ------------------------------
# Lightweight list endpoint (matches /api/tewa/scenarios/)
# ------------------------------


@api_view(["GET"])
def scenarios(_request):
    qs = Scenario.objects.all().order_by("id")
    return Response(ScenarioSerializer(qs, many=True).data)

# ------------------------------
# Compute Now (manual trigger) — persists via engine
# ------------------------------


@api_view(["POST"])
def compute_now(request):
    """
    Trigger a compute immediately for a scenario at current time.
    Body:
      - scenario_id (int, required)
      - method ('linear' | 'latest', default 'linear')
      - weapon_range_km (float, optional; used by scoring paths if needed)
    """
    scenario_id = request.data.get("scenario_id")
    method = request.data.get("method", "linear")
    when_iso = _iso_utc_now()

    if scenario_id is None:
        return _bad_request("scenario_id is required")

    try:
        compute_scores_at_timestamp(
            scenario_id=int(scenario_id),
            when_iso=when_iso,
            method=method
        )
        # Optionally: periodic background sweep
        # periodic_compute_threats.delay(int(scenario_id))
    except Exception as e:
        return Response({"detail": f"Compute failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        "status": "ok",
        "scenario_id": int(scenario_id),
        "method": method,
        "computed_at": when_iso
    }, status=status.HTTP_200_OK)

# ------------------------------
# Compute At (timestamped) — pure compute, no persistence
# ------------------------------


@csrf_exempt
@require_POST
def compute_at(request):
    """
    POST {scenario_id, when, da_ids?, method?, weapon_range_km?}
    Persists ThreatScore via engine (compute_scores_at_timestamp) and returns a status + count + scores.
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    scenario_id = body.get("scenario_id")
    when = parse_datetime(body.get("when") or "")
    if scenario_id is None:
        return JsonResponse({"detail": "scenario_id is required"}, status=400)
    if when is None:
        return JsonResponse({"detail": "Invalid 'when' datetime"}, status=400)
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    method = body.get("method", "linear")
    scenario_id_int = int(scenario_id)

    # Track how many rows existed before and mark a start time window
    before_count = ThreatScore.objects.filter(
        scenario_id=scenario_id_int).count()
    call_started = timezone.now()

    try:
        compute_scores_at_timestamp(
            scenario_id=scenario_id_int,
            when_iso=_iso_utc(when),
            method=method,
        )
    except Exception as e:
        return JsonResponse({"detail": f"Compute failed: {e}"}, status=500)

    after_count = ThreatScore.objects.filter(
        scenario_id=scenario_id_int).count()
    created = max(after_count - before_count, 0)

    # Collect rows created by this call (engine uses "now" for computed_at)
    window_start = call_started - timedelta(seconds=1)
    scores_qs = (
        ThreatScore.objects
        .filter(scenario_id=scenario_id_int, computed_at__gte=window_start)
        .select_related("track", "da")
        .order_by("-score")
    )

    scores_simple = [
        {
            "track_id": ts.track.track_id,
            "da_name": ts.da.name if ts.da_id else None,
            "score": float(ts.score),
            "computed_at": _iso_utc(ts.computed_at),
        }
        for ts in scores_qs
    ]

    return JsonResponse({
        "status": "ok",
        "scenario_id": scenario_id_int,
        "when": _iso_utc(when),
        "method": method,
        "count": created,
        "scores": scores_simple,
        # optional alias for clients expecting "threats"
        "threats": scores_simple,
    }, status=200)

# ------------------------------
# Ranking
# ------------------------------


@api_view(["GET"])
def threat_ranking(request):
    """
    GET /ranking/?scenario_id=&da_id=&top_n=
    """
    scenario_id = request.query_params.get("scenario_id")
    da_id = request.query_params.get("da_id")
    top_n = request.query_params.get("top_n")

    if not scenario_id:
        return _bad_request("scenario_id is required")

    try:
        scenario_id_int = int(scenario_id)
        da_id_int: Optional[int] = int(da_id) if da_id else None
        top_n_int: Optional[int] = int(top_n) if top_n else None
    except ValueError:
        return _bad_request("Invalid parameter type")

    try:
        results = rank_threats(
            scenario_id=scenario_id_int,
            da_id=da_id_int,
            top_n=top_n_int
        )
    except Exception as e:
        return Response({"detail": f"Failed to rank: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"scenario_id": scenario_id_int, "threats": results}, status=status.HTTP_200_OK)


# Alias so urls can use views.ranking or views.threat_ranking

# tewa/api/views.py

# tewa/api/views.py


@api_view(['GET'])
def ranking(request):
    scenario_id = request.query_params.get('scenario_id')
    # Default to 10 if not provided
    top_n = request.query_params.get('top_n', 10)
    da_id = request.query_params.get('da_id', None)

    # Validate scenario_id
    if not scenario_id:
        return JsonResponse({"error": "scenario_id is required"}, status=400)

    try:
        scenario_id = int(scenario_id)
        top_n = int(top_n)  # Ensure top_n is an integer
    except ValueError:
        return JsonResponse({"error": "Invalid scenario_id or top_n"}, status=400)

    # Rank the threats
    try:
        if da_id:
            da_id = int(da_id)
            try:
                da = DefendedAsset.objects.get(id=da_id)
                ranked_threats = rank_threats(
                    scenario_id, da_id=da_id, top_n=top_n)
            except DefendedAsset.DoesNotExist:
                return JsonResponse({"error": "DefendedAsset not found"}, status=404)
        else:
            ranked_threats = rank_threats(scenario_id, top_n=top_n)

        return JsonResponse(ranked_threats, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ------------------------------
# Legacy-compatible calculate_scores endpoint (pure compute)
# ------------------------------


@csrf_exempt
@require_POST
def calculate_scores(request):
    """
    POST JSON:
      - scenario_id (int, required)
      - when (ISO8601 string, required)
      - da_ids (list[int], optional)
      - method ('linear'|'latest', optional, default 'latest')
      - weapon_range_km (float, optional, default 20)
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    scenario_id = body.get("scenario_id")
    when = parse_datetime(body.get("when") or "")
    if scenario_id is None:
        return JsonResponse({"detail": "scenario_id is required"}, status=400)
    if when is None:
        return JsonResponse({"detail": "Invalid 'when' datetime"}, status=400)
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    try:
        scenario = Scenario.objects.get(id=int(scenario_id))
    except Scenario.DoesNotExist:
        return JsonResponse({"detail": f"Scenario {scenario_id} not found"}, status=404)

    da_ids = body.get("da_ids") or []
    das = list(DefendedAsset.objects.filter(id__in=da_ids)
               ) if da_ids else list(DefendedAsset.objects.all())
    method = body.get("method", "latest")
    weapon_range_km = float(body.get("weapon_range_km", 20))

    try:
        threats = calculate_scores_for_when(
            scenario=scenario,
            when=when,
            das=das,
            method=method,
            weapon_range_km=weapon_range_km
        )
    except Exception as e:
        return JsonResponse({"detail": f"Failed to compute: {e}"}, status=500)

    return JsonResponse({
        "scenario_id": int(scenario.pk),
        "computed_at": _iso_utc_now(),
        "threats": threats
    }, status=200)


@csrf_exempt  # Temporarily exempt from CSRF for testing (use with caution)
def upload_tracks(request):
    """
    Handle CSV upload for track data.
    Endpoint: POST /api/tewa/upload_tracks/
    """
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        try:
            file_content = file.read().decode('utf-8')  # Ensure we get the content
            result = import_csv(file_content)  # Process the CSV
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "No file provided"}, status=400)


@api_view(["GET"])
def score(request):
    """
    GET /api/tewa/score/?scenario_id=&da_id=&ordering=-score
    Returns serialized ThreatScore rows (compat with frontend).
    """
    scenario_id = request.query_params.get("scenario_id")
    da_id = request.query_params.get("da_id")
    ordering = request.query_params.get("ordering", "-score")

    qs = ThreatScore.objects.all()
    if scenario_id:
        qs = qs.filter(scenario_id=scenario_id)
    if da_id:
        qs = qs.filter(da_id=da_id)
    if ordering:
        qs = qs.order_by(ordering)

    return Response(ThreatScoreSerializer(qs, many=True).data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def da_list_api(request):
    if request.method == 'GET':
        das = DefendedAsset.objects.all().order_by('name')
        serializer = DefendedAssetSerializer(das, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = DefendedAssetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['POST'])
def da_create_api(request):
    serializer = DefendedAssetSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
def track_detail(request):
    """
    GET /api/tewa/tracks/?track_id=T1&scenario_id=1
    Returns detailed info about a specific track for a given scenario.
    """
    track_id = request.GET.get("track_id")
    scenario_id = request.GET.get("scenario_id")

    if not track_id or not scenario_id:
        return Response({"detail": "track_id and scenario_id are required"}, status=400)

    tracks = Track.objects.filter(
        track_id=track_id, scenario_id=scenario_id).order_by('-id')
    if not tracks.exists():
        return Response({"detail": "Track not found"}, status=404)

    track = tracks.first()  # pick latest by id
    serializer = TrackSerializer(track)

    # Include threat scores for all DAs
    threat_scores = track.threatscore_set.all().values(
        'da__name', 'score', 'computed_at'
    )
    data = serializer.data
    data['threat_scores'] = list(threat_scores)

    return Response(data)
