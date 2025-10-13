# tewa/api/views.py


from tewa.services.score_breakdown import get_score_breakdown
from rest_framework.decorators import api_view
import json
import uuid
from datetime import timedelta
from datetime import timezone as dt_timezone
from typing import Optional

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt  # keep only where truly needed
from django.views.decorators.http import require_POST

# ------------------------------
# Small helpers & query serializers
# ------------------------------
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from tewa.api.serializers import (
    DefendedAssetSerializer,
    ScenarioSerializer,
    ThreatScoreSerializer,
    TrackSampleSerializer,
    TrackSerializer,
    # Add small query serializers below
)
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample
from tewa.services.csv_import import import_csv
from tewa.services.engine import compute_scores_at_timestamp
from tewa.services.ranking import rank_threats
from tewa.services.score_breakdown_service import (
    ScoreBreakdownService,  # (kept for future use)
)
from tewa.services.threat_compute import calculate_scores_for_when


class RankingQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField(required=True)
    da_id = serializers.IntegerField(required=False, allow_null=True)
    top_n = serializers.IntegerField(
        required=False, default=10, min_value=1, max_value=100)


class ScoreListQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField(required=False)
    da_id = serializers.IntegerField(required=False)
    ordering = serializers.ChoiceField(
        required=False,
        default="-score",
        choices=("-score", "score", "-computed_at", "computed_at"),
    )


class ScoreBreakdownQuerySerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField()
    da_id = serializers.IntegerField()
    track_id = serializers.IntegerField()


def _iso_utc_now() -> str:
    return timezone.now().astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_utc(dt):
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def _bad_request(msg: str) -> Response:
    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


# ------------------------------
# Root
# ------------------------------

def root(_):
    return Response({
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
            "/api/tewa/score/breakdown",
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
    GET /api/tewa/score/?scenario_id=&da_id=&ordering=-score
    """
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

        # Keep payload lean
        qs = qs.only("id", "scenario_id", "da_id",
                     "track_id", "score", "computed_at")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DefendedAssetViewSet(viewsets.ModelViewSet):
    """Full CRUD for DAs."""
    queryset = DefendedAsset.objects.all()
    serializer_class = DefendedAssetSerializer


# ------------------------------
# Lightweight scenarios list (alias)
# ------------------------------

@api_view(["GET"])
def scenarios(_request):
    qs = Scenario.objects.all().order_by("id").only(
        "id", "name", "start_time", "end_time")
    return Response(ScenarioSerializer(qs, many=True).data)


# ------------------------------
# Compute Now — persists via engine
# ------------------------------

@api_view(["POST"])
def compute_now(request):
    """
    POST body:
      - scenario_id (int, required)
      - method ('linear' | 'latest', default 'linear')
    """
    scenario_id = request.data.get("scenario_id")
    method = request.data.get("method", "linear")

    if scenario_id is None:
        return _bad_request("scenario_id is required")

    try:
        scenario_id_int = int(scenario_id)
    except (TypeError, ValueError):
        return _bad_request("scenario_id must be an integer")

    when_iso = _iso_utc_now()
    batch_id = str(uuid.uuid4())  # tag rows created by this compute

    try:
        # Pass batch_id via kwargs to avoid Pylance's unknown-parameter warning.
        compute_scores_at_timestamp(
            scenario_id=scenario_id_int,
            when_iso=when_iso,
            method=method,
            **{"batch_id": batch_id},
        )
    except TypeError:
        # Engine not yet updated to accept batch_id
        compute_scores_at_timestamp(
            scenario_id=scenario_id_int,
            when_iso=when_iso,
            method=method,
        )
        batch_id = None
    except Exception as e:
        return Response({"detail": f"Compute failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {
            "status": "ok",
            "scenario_id": scenario_id_int,
            "method": method,
            "computed_at": when_iso,
            "batch_id": batch_id,
        },
        status=status.HTTP_200_OK,
    )
# ------------------------------
# Compute At — persists via engine and returns rows created
# ------------------------------


@api_view(["POST"])
def compute_at(request):
    """
    POST JSON:
      {
        "scenario_id": int,
        "when": ISO8601 string,
        "da_ids": [int] | null,
        "method": "linear" | "latest",
        "weapon_range_km": float | null
      }
    Persists ThreatScore rows and returns a summary of the rows created.
    """
    body = request.data or {}

    # scenario_id
    scenario_id = body.get("scenario_id")
    if scenario_id is None:
        return Response({"detail": "scenario_id is required"}, status=400)
    try:
        scenario_id_int = int(scenario_id)
    except (TypeError, ValueError):
        return Response({"detail": "scenario_id must be an integer"}, status=400)

    # when
    when = parse_datetime(body.get("when") or "")
    if when is None:
        return Response({"detail": "Invalid 'when' datetime"}, status=400)
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    # method
    method = body.get("method", "linear")

    # da_ids (Iterable[int] | None)
    da_ids_raw = body.get("da_ids", None)
    if da_ids_raw in (None, "", []):
        da_ids = None
    elif isinstance(da_ids_raw, list):
        try:
            da_ids = [int(x) for x in da_ids_raw]
        except (TypeError, ValueError):
            return Response({"detail": "da_ids must be a list of integers"}, status=400)
    else:
        return Response({"detail": "da_ids must be a list of integers or null"}, status=400)

    # weapon_range_km (float | None)
    wr_raw = body.get("weapon_range_km", None)
    if wr_raw in (None, ""):
        weapon_range_km: Optional[float] = None
    else:
        try:
            weapon_range_km = float(wr_raw)
        except (TypeError, ValueError):
            return Response({"detail": "weapon_range_km must be a number"}, status=400)

    # Prefer deterministic capture via batch_id, with runtime fallback if engine lacks support
    batch_id = str(uuid.uuid4())
    call_started = timezone.now()

    try:
        compute_scores_at_timestamp(
            scenario_id=scenario_id_int,
            when_iso=_iso_utc(when),
            method=method,
            da_ids=da_ids,
            weapon_range_km=weapon_range_km,
            # avoids Pylance warning; raises TypeError at runtime if unsupported
            **{"batch_id": batch_id},
        )
    except TypeError:
        compute_scores_at_timestamp(
            scenario_id=scenario_id_int,
            when_iso=_iso_utc(when),
            method=method,
            da_ids=da_ids,
            weapon_range_km=weapon_range_km,
        )
        batch_id = None
    except Exception as e:
        return Response({"detail": f"Compute failed: {e}"}, status=500)

    # Collect rows created by this call
    if batch_id:
        scores_qs = (
            ThreatScore.objects
            .filter(scenario_id=scenario_id_int, batch_id=batch_id)
            .select_related("track", "da")
            .only("score", "computed_at", "track__track_id", "da__name")
            .order_by("-score")
        )
    else:
        # Fallback (time-window). Slightly widened window to avoid clock skew.
        window_start = call_started - timedelta(seconds=2)
        scores_qs = (
            ThreatScore.objects
            .filter(scenario_id=scenario_id_int, computed_at__gte=window_start)
            .select_related("track", "da")
            .only("score", "computed_at", "track__track_id", "da__name")
            .order_by("-score")
        )

    scores_simple = [
        {
            "track_id": ts.track.track_id,
            "da_name": ts.da.name if getattr(ts, "da", None) else None,
            "score": float(ts.score) if ts.score is not None else None,
            "computed_at": _iso_utc(ts.computed_at) if ts.computed_at else None,
        }
        for ts in scores_qs
    ]

    return Response({
        "status": "ok",
        "scenario_id": scenario_id_int,
        "when": _iso_utc(when),
        "method": method,
        "count": len(scores_simple),
        "scores": scores_simple,
        "threats": scores_simple,  # alias
        "batch_id": batch_id,
    }, status=200)

# ------------------------------
# Ranking (single, unified endpoint)
# ------------------------------


@api_view(["GET"])
def ranking(request):
    """
    GET /api/tewa/ranking/?scenario_id=&da_id=&top_n=
    """
    q = RankingQuerySerializer(data=request.query_params)
    q.is_valid(raise_exception=True)
    vd = q.validated_data

    try:
        results = rank_threats(
            scenario_id=vd["scenario_id"],
            da_id=vd.get("da_id"),
            top_n=vd.get("top_n", 10),
        )
    except Exception as e:
        return Response({"detail": f"Failed to rank: {e}"}, status=500)

    # Keep compatibility with previous return shapes:
    return Response({"scenario_id": vd["scenario_id"], "threats": results})


# ------------------------------
# Legacy-compatible calculate_scores (pure compute, no persistence)
# ------------------------------

@require_POST
@csrf_exempt  # remove in prod if not needed
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
        return Response({"detail": "Invalid JSON"}, status=400)

    scenario_id = body.get("scenario_id")
    when = parse_datetime(body.get("when") or "")
    if scenario_id is None:
        return Response({"detail": "scenario_id is required"}, status=400)
    if when is None:
        return Response({"detail": "Invalid 'when' datetime"}, status=400)
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    try:
        scenario = Scenario.objects.get(id=int(scenario_id))
    except Scenario.DoesNotExist:
        return Response({"detail": f"Scenario {scenario_id} not found"}, status=404)

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
        return Response({"detail": f"Failed to compute: {e}"}, status=500)

    return Response({
        "scenario_id": int(scenario.pk),
        "computed_at": _iso_utc_now(),
        "threats": threats
    })


# ------------------------------
# CSV Upload
# ------------------------------

@require_POST
@csrf_exempt  # remove in prod; prefer session auth + CSRF or token auth
def upload_tracks(request):
    """
    Handle CSV upload for track data.
    Endpoint: POST /api/tewa/upload_tracks/
    """
    file = request.FILES.get('file')
    if not file:
        return Response({"detail": "No file provided"}, status=400)
    try:
        # Large files: use chunks if needed. Here we decode all for simplicity.
        content = file.read().decode('utf-8', errors='replace')
        result = import_csv(content)
        return Response(result)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)


# ------------------------------
# Score list alias (kept for compatibility with frontend)
# ------------------------------

@api_view(["GET"])
def score(request):
    """
    GET /api/tewa/score/?scenario_id=&da_id=&ordering=-score
    """
    return ThreatScoreViewSet.as_view({"get": "list"})(request)


# ------------------------------
# DA list/create (cleaned)
# ------------------------------

@api_view(['GET', 'POST'])
def da_list_api(request):
    if request.method == 'GET':
        das = DefendedAsset.objects.all().order_by(
            'name').only('id', 'name', 'lat', 'lon')
        return Response(DefendedAssetSerializer(das, many=True).data)
    # POST
    serializer = DefendedAssetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


# ------------------------------
# Track detail with scores
# ------------------------------

@api_view(['GET'])
def track_detail(request):
    """
    GET /api/tewa/tracks/?track_id=T1&scenario_id=1
    """
    track_id = request.GET.get("track_id")
    scenario_id = request.GET.get("scenario_id")

    if not track_id or not scenario_id:
        return Response({"detail": "track_id and scenario_id are required"}, status=400)

    tracks = Track.objects.filter(
        track_id=track_id, scenario_id=scenario_id).order_by('-id')
    if not tracks.exists():
        return Response({"detail": "Track not found"}, status=404)

    track = tracks.first()
    data = TrackSerializer(track).data

    # Include threat scores for all DAs (lean fields)
    threat_scores = (track.threatscore_set
                     .only("score", "computed_at", "da_id")
                     .select_related("da")
                     .values('da__name', 'score', 'computed_at'))
    data['threat_scores'] = [
        {
            "da_name": t["da__name"],
            "score": float(t["score"]) if t["score"] is not None else None,
            "computed_at": _iso_utc(t["computed_at"]) if t["computed_at"] else None,
        }
        for t in threat_scores
    ]
    return Response(data)


# ------------------------------
# Score Breakdown
# ------------------------------

class ScoreBreakdownView(APIView):
    """
    GET /api/tewa/score/breakdown?scenario_id=1&da_id=1&track_id=1
    """

    def get(self, request):
        q = ScoreBreakdownQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        d = q.validated_data

        ts = (ThreatScore.objects
              .filter(scenario_id=d["scenario_id"],
                      da_id=d["da_id"],
                      track_id=d["track_id"])
              .order_by("-computed_at", "-id")
              .only("computed_at", "cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score")
              .first())

        if not ts:
            return Response({"detail": "No ThreatScore found."}, status=404)

        body = {
            "scenario_id": d["scenario_id"],
            "da_id": d["da_id"],
            "track_id": d["track_id"],
            "ts": _iso_utc(ts.computed_at) if ts.computed_at else None,
            "cpa_km": float(ts.cpa_km) if ts.cpa_km is not None else None,
            "tcpa_s": float(ts.tcpa_s) if ts.tcpa_s is not None else None,
            "tdb_km": float(ts.tdb_km) if ts.tdb_km is not None else None,
            "twrp_s": float(ts.twrp_s) if ts.twrp_s is not None else None,
            "total_score": float(ts.score) if ts.score is not None else None,
        }
        return Response(body, status=200)


@api_view(['GET'])
def score_breakdown(request):
    scenario_id = int(request.query_params.get("scenario_id"))
    track_id = request.query_params.get("track_id")
    da_id = int(request.query_params.get("da_id"))

    result = get_score_breakdown(scenario_id, track_id, da_id)
    return Response(result)
