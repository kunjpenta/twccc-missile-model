# tewa/urls.py
from django.urls import path

from tewa.api import views as api_views

from . import views
from .views import score_breakdown_page, search_tracks, track_detail, upload_tracks_form

app_name = "tewa"

urlpatterns = [
    path("", api_views.root, name="root"),
    path("upload_tracks/", views.upload_tracks, name="upload_tracks"),
    path("scenarios/", views.list_scenarios, name="list_scenarios"),
    path("compute_now/", views.compute_now, name="compute_now"),
    path("scenario/<int:scenario_id>/",
         views.scenario_detail, name="scenario_detail"),
    path("scenario/<int:scenario_id>/compute_now/",
         views.compute_now_scenario, name="compute_now_scenario"),

    # DA CRUD
    path("das/", views.da_list, name="da_list"),
    path("das/create/", views.da_create, name="da_create"),
    path("das/<int:da_id>/edit/", views.da_edit, name="da_edit"),
    path("das/<int:da_id>/delete/", views.da_delete, name="da_delete"),

    # Tracks
    path("tracks/<str:track_id>/", track_detail, name="track_detail"),
    path("tracks/", search_tracks, name="search_tracks"),

    # Threat board
    path("threat_board/", views.threat_board, name="threat_board"),

    # Forms
    path("upload_tracks_form/", upload_tracks_form, name="upload_tracks_form"),

    # Score Breakdown (HTML page)
    path(
        "score/<int:scenario_id>/<int:da_id>/<int:track_id>/breakdown/",
        score_breakdown_page,
        name="score-breakdown-page",
    ),
    path(
        "score/breakdown/<int:scenario_id>/<int:da_id>/<int:track_id>/",
        api_views.ScoreBreakdownView.as_view(),
        name="score_breakdown_path",
    ),
]
