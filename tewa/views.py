# tewa/views.py

import csv
import io
import logging
from datetime import datetime
from io import StringIO

from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tewa.management.commands.compute_threats import Command

# Import models
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample
from tewa.serializers import TrackSerializer
from tewa.services.csv_import import import_csv  # <-- only this import_csv

# Import services
from tewa.services.engine import compute_scores_at_timestamp
from tewa.services.kinematics import (
    cpa_tcpa,
    time_to_da_boundary_s,
    time_to_weapon_release_s,
)
from tewa.services.ranking import rank_threats
from tewa.services.score_breakdown_service import ScoreBreakdownService
from tewa.services.scoring import combine_score

# Import forms
from .forms import DefendedAssetForm, UploadTrackForm
from .models import DefendedAsset, Track

# Import serializers
from .serializers import ScenarioSerializer, ThreatScoreSerializer, TrackSerializer


class ComputeThreat(APIView):
    """
    POST /api/tewa/score/ - Computes threat score for track vs defended asset at a given time.
    """

    def post(self, request):
        # Parse and validate input
        da_id = request.data.get("da_id")
        track_payload = request.data.get("track")
        weapon_range_km = request.data.get("weapon_range_km")

        if not da_id:
            return Response({"detail": "da_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(track_payload, dict):
            return Response({"detail": "track payload is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch DefendedAsset object
        da = get_object_or_404(DefendedAsset, id=da_id)

        # Upsert Track snapshot by track_id
        track, _ = Track.objects.update_or_create(
            track_id=track_payload["track_id"],
            defaults={
                "lat": track_payload["lat"],
                "lon": track_payload["lon"],
                "alt_m": track_payload["alt_m"],
                "speed_mps": track_payload["speed_mps"],
                "heading_deg": track_payload["heading_deg"],
            },
        )

        # Compute metrics
        cpa_res = cpa_tcpa(
            track.lat, track.lon, track.speed_mps, track.heading_deg, da.lat, da.lon
        )
        tcpa_s = cpa_res.tcpa_s
        cpa_km = cpa_res.cpa_km

        tdb_s = time_to_da_boundary_s(
            track.lat, track.lon, track.speed_mps, track.heading_deg, da.lat, da.lon, da.radius_km
        )

        twrp_s = None
        if weapon_range_km:
            twrp_s = time_to_weapon_release_s(
                track.lat, track.lon, track.speed_mps, track.heading_deg, da.lat, da.lon, weapon_range_km
            )

        # Calculate threat score
        score = combine_score(cpa_km=cpa_km, tcpa_s=tcpa_s,
                              tdb_s=tdb_s, twrp_s=twrp_s)

        # Save threat score to the database
        ts = ThreatScore.objects.create(
            track=track,
            da=da,
            cpa_km=cpa_km,
            tcpa_s=tcpa_s,
            tdb_km=None,  # Optional field for distance-to-boundary if required later
            twrp_s=twrp_s,
            score=score,
        )

        return Response(ThreatScoreSerializer(ts).data, status=status.HTTP_201_CREATED)


class ComputeThreatsAt(APIView):
    """
    POST /api/tewa/compute_at - Compute threat scores for a scenario at a specific timestamp.
    """

    def post(self, request):
        scenario_id = request.data.get("scenario_id")
        when = request.data.get("when")
        da_ids = request.data.get("da_ids")
        method = request.data.get("method", "linear")
        weapon_range_km = request.data.get("weapon_range_km")

        if not scenario_id or not when:
            return Response({"detail": "scenario_id and when are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            scores = compute_scores_at_timestamp(
                scenario_id=int(scenario_id),
                when_iso=str(when),
                da_ids=da_ids,
                method=method,
                weapon_range_km=weapon_range_km,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        data = ThreatScoreSerializer(scores, many=True).data
        return Response({"count": len(data), "scores": data})


logger = logging.getLogger(__name__)

'''rrerer
@api_view(['POST'])
def upload_tracks(request):
    file = request.FILES.get('file')

    if not file:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    if not file.name.endswith('.csv'):
        return JsonResponse({'error': 'Please upload a valid CSV file.'}, status=400)

    try:
        # Read the CSV file
        csv_file = io.StringIO(file.read().decode('utf-8'))
        reader = csv.DictReader(csv_file)

        for row in reader:
            try:
                track_id = row['track_id']
                lat = float(row['lat'])
                lon = float(row['lon'])
                alt_m = float(row['alt_m'])
                speed_mps = float(row['speed_mps'])
                heading_deg = float(row['heading_deg'])
                timestamp_str = row['timestamp']

                # Convert the timestamp from string to datetime object
                timestamp = datetime.strptime(
                    timestamp_str, "%Y-%m-%dT%H:%M:%SZ")

                # Use get_or_create() to avoid creating duplicate Tracks
                track, created = Track.objects.get_or_create(
                    track_id=track_id,
                    defaults={
                        'lat': lat,
                        'lon': lon,
                        'alt_m': alt_m,
                        'speed_mps': speed_mps,
                        'heading_deg': heading_deg,
                    }
                )

                # Use update_or_create() for TrackSample to prevent duplicates for same track_id and timestamp
                TrackSample.objects.update_or_create(
                    track=track,
                    t=timestamp,  # Use the parsed timestamp here
                    defaults={
                        'lat': lat,
                        'lon': lon,
                        'alt_m': alt_m,
                        'speed_mps': speed_mps,
                        'heading_deg': heading_deg
                    }
                )

            except KeyError as e:
                return JsonResponse({'error': f'Missing data for {e}'}, status=400)
            except ValueError as ve:
                logger.error(f"ValueError on row {row}: {ve}")
                return JsonResponse({'error': 'Invalid data format in CSV.'}, status=400)

        return JsonResponse({'message': 'File processed successfully.'}, status=200)

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return JsonResponse({'error': f'Error processing file: {str(e)}'}, status=500)

'''

# tewa/views.py


@api_view(["POST"])
@permission_classes([AllowAny])  # Optional: You can restrict this if needed
def upload_tracks(request):
    """
    Endpoint to handle CSV file upload and parse track data.
    The CSV file should be uploaded with the key 'file'.
    Scenario ID should also be provided in the POST data as 'scenario_id'.
    """

    # Get the uploaded file from the request
    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "No file provided as 'file'."}, status=400)

    try:
        # Optional: Get the scenario_id from POST data
        scenario_id = request.POST.get("scenario_id")

        if not scenario_id:
            return Response({"detail": "Scenario ID is required."}, status=400)

        # Decode the uploaded file's content to string (UTF-8)
        text = f.read().decode("utf-8", errors="replace")

        # Assuming `import_csv` is a utility function that parses the CSV and imports the data
        summary = import_csv(text, scenario_id=int(scenario_id))

        return Response({"message": "Upload successful", **summary}, status=200)

    except Exception as e:
        # Return error if there's any exception in the process
        return Response({"detail": str(e)}, status=400)


@api_view(['GET'])
def list_scenarios(request):
    scenarios = Scenario.objects.all()
    serializer = ScenarioSerializer(scenarios, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def compute_now(request):
    """
    Compute threat scores immediately for a given scenario and timestamp.
    Request body:
    {
        "scenario_id": 1,
        "timestamp": "2025-09-30T06:05:00Z",  # optional
        "weapon_range_km": 10.0               # optional
    }
    """
    data = request.data
    scenario_id = data.get('scenario_id')
    timestamp = data.get('timestamp', timezone.now().isoformat())
    weapon_range = data.get('weapon_range_km', None)

    if not scenario_id:
        return Response({"error": "scenario_id is required."}, status=400)

    try:
        scenario = Scenario.objects.get(id=scenario_id)
    except Scenario.DoesNotExist:
        return Response({"error": f"Scenario {scenario_id} does not exist."}, status=404)

    scores = compute_scores_at_timestamp(
        scenario_id=scenario_id,
        when_iso=timestamp,
        weapon_range_km=weapon_range
    )

    # Return simplified response
    response_data = [
        {
            "track_id": s.track.track_id,
            "da_name": s.da.name,
            "cpa_km": s.cpa_km,
            "tcpa_s": s.tcpa_s,
            "tdb_km": s.tdb_km,
            "twrp_s": s.twrp_s,
            "score": s.score
        }
        for s in scores
    ]
    return Response(response_data)


def create_defended_asset(request):
    if request.method == 'POST':
        form = DefendedAssetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('da_list')
    else:
        form = DefendedAssetForm()
    return render(request, 'create_da.html', {'form': form})


# tewa/views.py


def home(request):
    scenarios = Scenario.objects.all()
    return render(request, 'home.html', {'scenarios': scenarios})


def scenario_detail(request, scenario_id):
    scenario = get_object_or_404(Scenario, pk=scenario_id)

    if request.method == "POST":
        # Trigger threat computation for this scenario
        command = Command()
        command.handle(scenario_id=scenario.id)
        return redirect('scenario_detail', scenario_id=scenario.id)

    return render(request, 'scenario_detail.html', {'scenario': scenario})


@require_POST
def compute_now_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    command = Command()
    das = DefendedAsset.objects.all()  # Or filter per scenario if needed

    # Call handle for each DA
    for da in das:
        command.handle(scenario_id=scenario.id, da_id=da.id)

    return redirect('tewa:scenario_detail', scenario_id=scenario.id)


# tewa/views.py


def da_list(request):
    das = DefendedAsset.objects.all()
    return render(request, 'da_list.html', {'das': das})


def da_create(request):
    if request.method == 'POST':
        form = DefendedAssetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tewa:da_list')  # <--- use namespaced URL
    else:
        form = DefendedAssetForm()
    return render(request, 'da_form.html', {'form': form, 'action': 'Add'})


def da_edit(request, da_id):
    da = get_object_or_404(DefendedAsset, pk=da_id)
    if request.method == 'POST':
        form = DefendedAssetForm(request.POST, instance=da)
        if form.is_valid():
            form.save()
            return redirect('tewa:da_list')
    else:
        form = DefendedAssetForm(instance=da)
    return render(request, 'da_form.html', {'form': form, 'action': 'Edit'})


def da_delete(request, da_id):
    da = get_object_or_404(DefendedAsset, pk=da_id)
    if request.method == "POST":
        da.delete()
        return redirect('tewa:da_list')
    return render(request, 'da_confirm_delete.html', {'da': da})


# tewa/views.py


@api_view(['GET'])
def search_tracks(request):
    """
    GET /api/tewa/tracks/?track_id=T1&scenario_id=1
    Supports filtering by track_id and scenario_id
    """
    tracks = Track.objects.all()

    track_id = request.GET.get('track_id')
    scenario_id = request.GET.get('scenario_id')

    if track_id:
        tracks = tracks.filter(track_id__icontains=track_id)
    if scenario_id:
        tracks = tracks.filter(scenario_id=scenario_id)

    serializer = TrackSerializer(tracks, many=True)
    return Response(serializer.data)


def upload_tracks_form(request):
    return render(request, 'upload_tracks.html')


# tewa/views.py


@api_view(['GET'])
def tracks_list(request):
    track_id = request.GET.get('track_id')
    scenario_id = request.GET.get('scenario_id')

    qs = Track.objects.all()
    if track_id:
        qs = qs.filter(track_id=track_id)
    if scenario_id:
        qs = qs.filter(scenario_id=scenario_id)

    serializer = TrackSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def track_detail(request, track_id):
    track = Track.objects.filter(track_id=track_id).first()
    if not track:
        return Response({"detail": "Track not found"}, status=404)
    serializer = TrackSerializer(track)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def threat_board(request):
    """
    GET /api/tewa/threat_board/
    Query Params:
      - scenario_id: ID of the scenario
      - da_id (optional): ID of the DA (if omitted, return all DAs)
      - top_n (optional): limit number of threats per DA, default=10
    """
    scenario_id = request.GET.get("scenario_id")
    da_id = request.GET.get("da_id", None)
    top_n = int(request.GET.get("top_n", 10))

    if not scenario_id:
        return Response({"detail": "scenario_id is required"}, status=400)

    try:
        da_id = int(da_id) if da_id else None
        scenario_id = int(scenario_id)
        board = rank_threats(scenario_id=scenario_id, da_id=da_id, top_n=top_n)
        return Response(board)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)

# tewa/views.py


def track_browser_page(request):
    """
    Serves the track browser HTML page for API testing.
    """
    return render(request, 'track_browser.html')


def score_breakdown_page(request, scenario_id: int, da_id: int, track_id: int):
    ts = (ThreatScore.objects
          .filter(scenario_id=scenario_id,
                  da_id=da_id,
                  track_id=track_id)
          .order_by("-computed_at", "-id")
          .first())
    if not ts:
        raise Http404("No ThreatScore found. Run compute and try again.")

    dto = {
        "scenario_id": scenario_id,
        "da_id": da_id,
        "track_id": track_id,
        "ts": ts.computed_at.isoformat() if ts.computed_at else "",
        "cpa": float(ts.cpa),
        "tcpa": float(ts.tcpa),
        "tdb": float(ts.tdb),
        "twrp": float(ts.twrp),
        "cpa_n": float(ts.cpa_n) if ts.cpa_n is not None else None,
        "tcpa_n": float(ts.tcpa_n) if ts.tcpa_n is not None else None,
        "tdb_n": float(ts.tdb_n) if ts.tdb_n is not None else None,
        "twrp_n": float(ts.twrp_n) if ts.twrp_n is not None else None,
        "total_score": float(ts.total_score) if ts.total_score is not None else None,
        "details": ts.details if hasattr(ts, "details") else None,
    }
    # NOTE: your file is tewa/templates/score_breakdown.html (no folder prefix)
    return render(request, "score_breakdown.html", {"dto": dto})
