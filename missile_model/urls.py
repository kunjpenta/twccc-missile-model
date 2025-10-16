# missile_model/urls.py
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path


def home(_request):
    return HttpResponse("Home")


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Core TEWA API (REST endpoints)
    path("api/tewa/", include(("tewa.api.urls", "tewa_api"), namespace="tewa_api")),

    # TEWA web routes (HTML / login / dashboards)
    path("", include(("tewa.urls", "tewa"), namespace="tewa")),

    # Health check
    path("health/", health, name="health"),

    # Django built-in login/logout (accounts/login, etc.)
    path("accounts/", include("django.contrib.auth.urls")),
]
