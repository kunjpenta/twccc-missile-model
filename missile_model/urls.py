# missile_model/urls.py
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path


def home(_request):
    return HttpResponse("Home")


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    # Mount API under a single prefix
    path("api/tewa/", include("tewa.api.urls")),

    # Optional site views (non-API). Keep only if tewa/urls.py exists.
    # path("tewa/", include("tewa.urls")),

    path("", home, name="home"),
    path("health/", health, name="health"),
]
