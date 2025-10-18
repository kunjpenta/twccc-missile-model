# missile_model/urls.py
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

# ⬇️ import the real DRF view
from tewa.api.views_compute import score_breakdown as score_breakdown_drf


@csrf_exempt
@require_GET
def public_score_breakdown_ok(request, *args, **kwargs):
    # IMPORTANT: this is a plain Django view — pass the raw HttpRequest
    # to the DRF-decorated view; it will wrap it and return a DRF Response.
    return score_breakdown_drf(request, *args, **kwargs)


def home(_request):
    return HttpResponse("Home")


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Put this BEFORE any includes so it wins resolution
    path("api/tewa/score_breakdown",
         public_score_breakdown_ok, name="score_breakdown"),

    # Admin
    path("admin/", admin.site.urls),

    # Core TEWA API (REST endpoints)
    path("api/tewa/", include(("tewa.api.urls", "tewa_api"), namespace="tewa_api")),

    # TEWA web routes (HTML / login / dashboards)
    path("", include(("tewa.urls", "tewa"), namespace="tewa")),
    path("", include(("core.urls", "core"), namespace="core")),  # <-- add/keep this


    # Health check
    path("health/", health, name="health"),

    # Other APIs
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/core/", include(("core.api.urls", "core_api"), namespace="core_api")),
    path("api/engagements/", include(("engagements.api.urls",
         "engagements_api"), namespace="engagements_api")),

    path("docs/", include("core.urls_docs", namespace="docs")),

]
