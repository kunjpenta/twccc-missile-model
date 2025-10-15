# tewa/api/view_utils.py
from datetime import timezone as dt_timezone

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response


def iso_utc(dt):
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def iso_utc_now():
    return iso_utc(timezone.now())


def bad_request(msg: str) -> Response:
    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
