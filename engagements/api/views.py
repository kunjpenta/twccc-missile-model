from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

# Reuse the existing ok() helper
from tewa.api.view_utils import ok


class BMCEngagementSummaryViewSet(ReadOnlyModelViewSet):
    """
    TODO: replace with real queryset/serializer.
    For now, return an empty list on list() and 404 on retrieve().
    """
    permission_classes = [IsAuthenticated]
    queryset = []  # DRF expects iterable; list keeps it simple
    serializer_class = None  # not used in our overridden list()

    def list(self, request, *args, **kwargs):
        return Response([])


class EngagementViewSet(ModelViewSet):
    """
    TODO: wire real model + serializer.
    For now, return 200 OK with a stub payload on list/create.
    """
    permission_classes = [IsAuthenticated]
    queryset = []
    serializer_class = None

    def list(self, request, *args, **kwargs):
        return Response({"ok": True, "endpoint": "engagements.engagements.list"})

    def create(self, request, *args, **kwargs):
        return Response({"ok": True, "endpoint": "engagements.engagements.create", "received": request.data})


class AssignTrackWidgetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return ok("engagements.assign_track_widget", received=request.data)

    def get(self, request, *args, **kwargs):
        return ok("engagements.assign_track_widget.get")
