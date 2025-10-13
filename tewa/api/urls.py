# tewa/api/urls.py
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from . import views as api
from .views import ScoreBreakdownView

# Keep app_name only if you plan to include with a namespace and use tewa_api:... in reverse().
# app_name = "tewa_api"

router = DefaultRouter()
router.register(r"scenario",    api.ScenarioViewSet,     basename="scenario")
router.register(r"da",          api.DefendedAssetViewSet, basename="da")
router.register(r"track",       api.TrackViewSet,        basename="track")
router.register(r"tracksample", api.TrackSampleViewSet,
                basename="tracksample")
router.register(r"threatscore", api.ThreatScoreViewSet,
                basename="threatscore")

urlpatterns = [
    # root + router
    path("", api.root, name="root"),
    path("", include(router.urls)),

    # Single (and only) score breakdown route — matches reverse("score-breakdown")
    path("score/breakdown", ScoreBreakdownView.as_view(), name="score-breakdown"),
    # Function endpoints (support both with/without trailing slash)
    re_path(r"^scenarios/?$",           api.scenarios,         name="scenarios"),
    re_path(r"^score/?$",               api.score,             name="score"),
    re_path(r"^ranking/?$",             api.ranking,           name="ranking"),
    re_path(r"^compute_now/?$",
            csrf_exempt(api.compute_now),      name="compute_now"),
    re_path(r"^compute_at/?$",
            csrf_exempt(api.compute_at),       name="compute_at"),
    re_path(r"^upload_tracks/?$",
            csrf_exempt(api.upload_tracks),    name="upload_tracks"),
    re_path(r"^calculate_scores/?$",
            csrf_exempt(api.calculate_scores), name="calculate_scores"),

    # Track detail by id
    re_path(r"^tracks/(?P<track_id>[^/]+)/?$",
            api.track_detail, name="track_detail"),
]


urlpatterns = [

]
