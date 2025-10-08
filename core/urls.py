# core/urls.py
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from .views import api_root, db_ping, health, index


def core_root(_):
    # Shown at GET /api/  (together with api_index above if you like, or keep this to subpaths)
    return JsonResponse({
        "name": "Core API",
        "endpoints": ["/api/health", "/api/db-ping"]
    })


urlpatterns = [

    path('health', health, name='health'),
    path('', index, name='index'),
    path('api/', api_root, name='api_root'),
    path('api/health', health, name='api_health'),
    path('db-ping', db_ping, name='db_ping'),
    path('api/tewa/', include('tewa.api.urls')),
    path('admin/', admin.site.urls),



]
