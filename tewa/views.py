# tewa/views.py

from __future__ import annotations

import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from tewa.management.commands.compute_threats import (
    Command,  # adjust import path if different
)
from tewa.models import DefendedAsset, Scenario, ThreatScore, Track
from tewa.services.charting import render_score_history_png
from tewa.services.score_history import get_score_series

from .forms import DefendedAssetForm, ScenarioParamsForm
from .models import ModelParams

logger = logging.getLogger(__name__)


# ---------- Home & Scenario pages ----------

def home(request):
    scenarios = Scenario.objects.all().order_by("id")
    return render(request, "home.html", {"scenarios": scenarios})


def scenario_detail(request, scenario_id: int):
    """
    Display Scenario details page:
      - Shows Defended Assets and Tracks with pagination.
      - On POST, triggers compute command for this scenario.
    """
    scenario = get_object_or_404(Scenario, pk=scenario_id)

    # Handle "Compute Now" button submission
    if request.method == "POST":
        cmd = Command()
        cmd.handle(scenario_id=scenario.id)
        return redirect("tewa:scenario_detail", scenario_id=scenario.id)

    # Query all Defended Assets for this scenario
    defended_assets = DefendedAsset.objects.filter(
        scenario=scenario
    ).order_by("id")

    # Paginate tracks for readability
    track_list = Track.objects.filter(scenario=scenario).order_by("id")
    paginator = Paginator(track_list, 10)
    page_number = request.GET.get("page")
    tracks = paginator.get_page(page_number)

    # Render the HTML view
    return render(request, "scenario_detail.html", {
        "scenario": scenario,
        "defended_assets": defended_assets,
        "tracks": tracks,
    })


@require_POST
def compute_now_scenario(request, scenario_id: int):
    """HTML button handler that kicks off compute for a scenario."""
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    cmd = Command()

    # If you want per-DA runs, modify this to filter by scenario_id
    for da in DefendedAsset.objects.filter(scenario=scenario):
        cmd.handle(scenario_id=scenario.id, da_id=da.id)

    return redirect("tewa:scenario_detail", scenario_id=scenario.id)


# ---------- DA CRUD (HTML) ----------

def da_list(request):
    das = DefendedAsset.objects.all().order_by("name")
    return render(request, "da_list.html", {"das": das})


def da_create(request):
    if request.method == "POST":
        form = DefendedAssetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("da_list")
    else:
        form = DefendedAssetForm()
    return render(request, "da_form.html", {"form": form, "action": "Add"})


def da_edit(request, da_id: int):
    da = get_object_or_404(DefendedAsset, pk=da_id)
    if request.method == "POST":
        form = DefendedAssetForm(request.POST, instance=da)
        if form.is_valid():
            form.save()
            return redirect("da_list")
    else:
        form = DefendedAssetForm(instance=da)
    return render(request, "da_form.html", {"form": form, "action": "Edit"})


def da_delete(request, da_id: int):
    da = get_object_or_404(DefendedAsset, pk=da_id)
    if request.method == "POST":
        da.delete()
        return redirect("da_list")
    return render(request, "da_confirm_delete.html", {"da": da})


# ---------- Lightweight HTML pages ----------

def upload_tracks_form(request):
    """Simple HTML page with a file input that posts to the API /api/tewa/upload_tracks/."""
    return render(request, "upload_tracks.html")


def track_browser_page(request):
    """HTML page for browsing tracks via the API."""
    return render(request, "track_browser.html")


def score_breakdown_page(request, scenario_id: int, da_id: int, track_id: int):
    """
    Server-rendered page showing the latest ThreatScore row for a specific (scenario, DA, track).
    """
    ts = (
        ThreatScore.objects
        .filter(scenario_id=scenario_id, da_id=da_id, track_id=track_id)
        .order_by("-computed_at", "-id")
        .first()
    )
    if not ts:
        raise Http404("No ThreatScore found. Run compute and try again.")

    dto = {
        "scenario_id": scenario_id,
        "da_id": da_id,
        "track_id": track_id,
        "ts": ts.computed_at.isoformat() if ts.computed_at else "",
        # Use actual field names from the model:
        "cpa_km": float(ts.cpa_km) if ts.cpa_km is not None else None,
        "tcpa_s": float(ts.tcpa_s) if ts.tcpa_s is not None else None,
        "tdb_km": float(ts.tdb_km) if ts.tdb_km is not None else None,
        "twrp_s": float(ts.twrp_s) if ts.twrp_s is not None else None,
        "total_score": float(ts.score) if ts.score is not None else None,
        # If you later add a JSON field for details, you can surface it here
        "details": getattr(ts, "details", None),
    }
    return render(request, "score_breakdown.html", {"dto": dto})


# tewa/views.py


# Optional compute trigger (best-effort)
def _trigger_compute_now(scenario_id: int) -> None:
    """
    Try to trigger compute via Celery task if available.
    Fails silently if Celery or the task isn't configured — the UI still saves.
    """
    try:
        from .tasks import compute_threats  # type: ignore
        # Your task likely takes scenario_id or scenario name.
        compute_threats.delay(scenario_id=scenario_id)
    except Exception:
        # No celery / no task — ignore
        pass


def scenario_assumptions_view(request: HttpRequest, scenario_id: int) -> HttpResponse:
    """
    Public (read-only) GET; staff/superuser-only POST.
    Shows/edits ModelParams defaults for a Scenario (R_W_m, R_DA_m, tick_s, weights, sigmas).
    """
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    params, _ = ModelParams.objects.get_or_create(scenario=scenario)

    # Edit permission only for authenticated staff/superusers
    can_edit = request.user.is_authenticated and (
        request.user.is_staff or request.user.is_superuser)

    if request.method == "POST":
        if not can_edit:
            return HttpResponseForbidden("Login required (staff) to edit scenario assumptions.")

        form = ScenarioParamsForm(request.POST, instance=params)
        if form.is_valid():
            # Optional audit field if your model has it
            if hasattr(params, "updated_by"):
                form.instance.updated_by = request.user
            form.save()

            if "compute_now" in request.POST:
                _trigger_compute_now(scenario.id)
                messages.success(
                    request, "Scenario defaults saved. Recompute started.")
            else:
                messages.success(request, "Scenario defaults saved.")

            return redirect("tewa:scenario_assumptions", scenario_id=scenario.id)
    else:
        form = ScenarioParamsForm(instance=params)

    # Read-only widgets for non-editors (public GET)
    if not can_edit:
        for f in form.fields.values():
            f.widget.attrs["disabled"] = "disabled"
            f.widget.attrs["readonly"] = "readonly"

    return render(
        request,
        "scenarios/assumptions.html",
        {
            "scenario": scenario,
            "form": form,
            "can_edit": can_edit,   # template can hide Save buttons when False
            "params": params,
        },
    )


# tewa/api/views.py (append)


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def score_history_png_view(request):
    try:
        scenario_id = int(request.GET["scenario_id"])
        da_id = int(request.GET["da_id"])
        track_id = request.GET["track_id"]
    except KeyError:
        return HttpResponseBadRequest("scenario_id, da_id, track_id are required")
    except ValueError:
        return HttpResponseBadRequest("IDs must be integers")

    dt_from = request.GET.get("from")
    dt_to = request.GET.get("to")
    try:
        width = int(request.GET.get("width", 800))
        height = int(request.GET.get("height", 300))
        smooth_q = request.GET.get("smooth")
        smooth = int(smooth_q) if smooth_q else None
    except ValueError:
        return HttpResponseBadRequest("width/height/smooth must be integers")

    series = get_score_series(scenario_id, da_id, track_id, dt_from, dt_to)
    if not series:
        raise Http404("No score history found")

    png = render_score_history_png(
        series, width=width, height=height, smooth=smooth)

    resp = HttpResponse(png, content_type="image/png")
    last_ts = series[-1][0]
    if last_ts:
        resp["Last-Modified"] = last_ts.strftime("%a, %d %b %Y %H:%M:%S GMT")
    resp["Cache-Control"] = "private, max-age=60"
    return resp
