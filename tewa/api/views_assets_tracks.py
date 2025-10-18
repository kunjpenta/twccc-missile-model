# tewa/api/views_assets_tracks.py

from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tewa.api.serializers import DefendedAssetSerializer, TrackSerializer
from tewa.models import DefendedAsset, Track

from .view_utils import ok


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class DefendedAssetViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DefendedAssetSerializer
    pagination_class = None  # DA list is usually short

    def get_queryset(self):
        qs = DefendedAsset.objects.all()
        # use Django's GET (no typing error)
        scenario_id = self.request.GET.get("scenario_id")
        if scenario_id:
            qs = qs.filter(scenario_id=scenario_id)
        return qs.order_by("id")


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TrackSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Track.objects.all()
        scenario_id = self.request.GET.get("scenario_id")  # use Django's GET
        if scenario_id:
            qs = qs.filter(scenario_id=scenario_id)
        return qs.order_by("id")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_trk_iden_data(request: Request) -> Response:
    return ok("core.track.get_trk_iden_data")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_mavlink_vs_flight(request: Request) -> Response:
    return ok("core.track.get_mavlink_vs_flight")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def insert_track_data(request: Request) -> Response:
    return ok("core.track.insert_track_data", received=request.data)
