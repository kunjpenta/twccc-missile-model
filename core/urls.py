# core/urls.py

from django.contrib import admin
from django.urls import path

from .views import api_root, db_ping, health, index

app_name = "core"

urlpatterns = [
    path("", index, name="index"),                 # GET /
    path("health/", health, name="health"),        # GET /health/
    path("db-ping/", db_ping, name="db_ping"),     # GET /db-ping/
    path("api/", api_root, name="api_root"),       # GET /api/
    path("api/health/", health, name="api_health"),  # GET /api/health/
    path("admin/", admin.site.urls),               # /admin/
]
