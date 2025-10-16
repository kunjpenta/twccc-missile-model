# tewa/api/urls.py
from django.http import JsonResponse
from django.urls import path
from django.utils.translation import activate
from rest_framework.routers import DefaultRouter

from tewa.api import views_assets_tracks

from . import views
from .views import (
    ScenarioParamsView,
    score_breakdown,  # <- function view
    score_history_png_view,  # <- function view
)

activate("en")


router = DefaultRouter()
router.register(r"scenario",     views.ScenarioViewSet,
                basename="scenario")
router.register(r"da",           views.DefendedAssetViewSet, basename="da")
router.register(r"track",        views.TrackViewSet,         basename="track")
router.register(r"tracksample",  views.TrackSampleViewSet,
                basename="tracksample")
router.register(r"threatscore",  views.ThreatScoreViewSet,
                basename="threatscore")
router = DefaultRouter()
router.register(r'defendedassets',
                views_assets_tracks.DefendedAssetViewSet, basename='defendedasset')
router.register(r'tracks', views_assets_tracks.TrackViewSet, basename='track')

# --- quick ping to verify we’re editing the right file ---


def ping(_): return JsonResponse({"ok": True})


urlpatterns = [
    path("ping", ping, name="ping"),  # /api/tewa/ping -> {"ok": true}

    path("", views.root, name="root"),
    path("scenarios/", views.scenarios, name="scenarios"),
    path("score/", views.score, name="score-list-alias"),

    # compute / analytics / uploads
    # intentionally no trailing slash
    path("compute_at", views.compute_at, name="compute-at"),
    path("compute_now/", views.compute_now, name="compute_now"),
    path("ranking/", views.ranking, name="ranking"),
    path("calculate_scores/", views.calculate_scores, name="calculate_scores"),
    path("upload_tracks/", views.upload_tracks, name="upload_tracks"),

    # Task 21 — Score breakdown (both spellings)
    path("score-breakdown",  score_breakdown, name="score-breakdown"),
    path("score_breakdown/", score_breakdown, name="score_breakdown_alias"),

    # Task 22 — CSV export
    path("export/threat_board.csv", views.export_threat_board_csv,
         name="export_threat_board_csv"),

    # Task 23 — Scenario params
    path("scenarios/<int:scenario_id>/params/",
         ScenarioParamsView.as_view(), name="scenario_params"),

    # Task 24 — PNG chart
    path("charts/score_history.png",
         score_history_png_view, name="score_history_png"),
    path("score_breakdown",  score_breakdown, name="score_breakdown"),
    path("score_history.png", score_history_png_view, name="score_history_png"),
    # Add alias for v1 API
    path("v1/compute_now/", views.compute_now, name="compute_now_v1"),
    path(
        "api/threatscores/<int:scenario_id>/",
        views.api_threatscores,
        name="api_threatscores",
    ),

]

urlpatterns += router.urls
