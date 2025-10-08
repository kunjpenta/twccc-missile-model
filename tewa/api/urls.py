# tewa/api/urls.py
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from . import views
from .views import (
    DefendedAssetViewSet,
    ScenarioViewSet,
    ThreatScoreViewSet,
    TrackSampleViewSet,
    TrackViewSet,
    da_list_api,
)

app_name = "tewa_api"

router = DefaultRouter()
router.register(r"scenario",      ScenarioViewSet,    basename="scenario")
router.register(r"da",            DefendedAssetViewSet, basename="da")
router.register(r"track",         TrackViewSet,       basename="track")
router.register(r"tracksample",   TrackSampleViewSet, basename="tracksample")
router.register(r"threatscore",   ThreatScoreViewSet, basename="threatscore")

urlpatterns = [
    # Router root (Browsable API for the viewsets)
    path("", views.root, name="root"),
    path("", include(router.urls)),
    path("upload_tracks/", views.upload_tracks, name="upload_tracks"),


    # Function endpoints — accept with OR without trailing slash to avoid 301 in tests
    re_path(r"^scenarios/?$",        views.scenarios,
            name="scenarios"),
    re_path(r"^upload_tracks/?$",    csrf_exempt(views.upload_tracks),
            name="upload_tracks"),
    re_path(r"^compute_now/?$",      csrf_exempt(views.compute_now),
            name="compute_now"),

    re_path(r"^score/?$",            views.score,
            name="score"),
    re_path(r"^ranking/?$",          views.ranking,
            name="ranking"),
    re_path(r"^calculate_scores/?$",
            csrf_exempt(views.calculate_scores), name="calculate_scores"),
    re_path(r"^compute_at/?$", csrf_exempt(views.compute_at), name="compute_at"),
    path('ranking/', views.ranking, name='ranking'),
    path('das/', da_list_api, name='da_list_api'),
    path('tracks/<str:track_id>/', views.track_detail, name='track_detail'),



]
