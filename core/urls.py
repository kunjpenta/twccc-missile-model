# core/urls.py
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from .views import api_root, db_ping, health, index

app_name = "core"

urlpatterns = [
    path("", index, name="index"),                               # GET /
    path("health/", health, name="health"),                      # GET /health/
    path("db-ping/", db_ping, name="db_ping"),                   # GET /db-ping/
    path("api/", api_root, name="api_root"),                     # GET /api/
    # GET /api/health/
    path("api/health/", health, name="api_health"),
    path("admin/", admin.site.urls),                             # /admin/

    # Docs pages (served from templates/docs/*.html or pages/docs/*.html)
    path("docs/", TemplateView.as_view(template_name="pages/docs/index.html"),
         name="docs-index"),
    path("docs/frontend/", TemplateView.as_view(template_name="pages/docs/frontend.html"),
         name="docs-frontend"),
    path("docs/backend/", TemplateView.as_view(template_name="pages/docs/backend.html"),
         name="docs-backend"),
    path("docs/database/", TemplateView.as_view(template_name="pages/docs/database.html"),
         name="docs-database"),
    
]
