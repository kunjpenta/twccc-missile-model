# tewa/api/urls.py
from django.urls import path
from django.utils.translation import activate
from rest_framework.routers import DefaultRouter

from . import views
from .views import (
    ScenarioParamsView,
    score_history_png_view,  # ← import the view
)

activate("en")  # harmless with USE_I18N=False; fine to keep

router = DefaultRouter()
router.register(r"scenario",     views.ScenarioViewSet,
                basename="scenario")
router.register(r"da",           views.DefendedAssetViewSet, basename="da")
router.register(r"track",        views.TrackViewSet,         basename="track")
router.register(r"tracksample",  views.TrackSampleViewSet,
                basename="tracksample")
router.register(r"threatscore",  views.ThreatScoreViewSet,
                basename="threatscore")

urlpatterns = [
    path("", views.root, name="root"),
    path("scenarios/", views.scenarios, name="scenarios"),
    path("score/", views.score, name="score-list-alias"),

    # compute / analytics / uploads
    path("compute_at", views.compute_at, name="compute-at"),  # no trailing slash
    path("compute_now/", views.compute_now, name="compute_now"),
    path("ranking/", views.ranking, name="ranking"),
    path("calculate_scores/", views.calculate_scores, name="calculate_scores"),
    path("upload_tracks/", views.upload_tracks, name="upload_tracks"),

    # score breakdown (the name used by tests)
    path("score-breakdown", views.score_breakdown, name="score-breakdown"),

    # querystring-based track detail
    path("tracks/detail/", views.track_detail, name="track-detail"),
    path("debug/score", views.score_breakdown_debug,
         name="score-breakdown-debug"),
    path("export/threat_board.csv", views.export_threat_board_csv,
         name="export_threat_board_csv"),
    path("scenarios/<int:scenario_id>/params/",
         ScenarioParamsView.as_view(), name="scenario_params"),
    path("charts/score_history.png",
         score_history_png_view, name="score_history_png"),


]

urlpatterns += router.urls



