# core/views.py

from django.db import connection
from django.http import JsonResponse


def index(request):
    # Site root
    return JsonResponse({
        "name": "Missile Model / TEWA API",
        "links": {
            "api_root": "/api/",
            "health": "/api/health",
            "tewa_root": "/api/tewa/",
            "admin": "/admin/"
        }
    })


def api_root(request):
    # API root
    return JsonResponse({
        "status": "ok",
        "endpoints": {
            "health": "/api/health",
            "tewa": "/api/tewa/"
        }
    })


def health(request):
    return JsonResponse({"status": "ok"})


def db_ping(request):
    with connection.cursor() as cur:
        cur.execute("SELECT 1;")
        row = cur.fetchone()
    return JsonResponse({"db": "ok" if row == (1,) else "fail"})
