# tewa/api/views_misc.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    endpoint = request.resolver_match.view_name if getattr(
        request, "resolver_match", None) else "ping"
    return Response({"ok": True, "endpoint": endpoint})
