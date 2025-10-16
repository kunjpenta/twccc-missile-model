# tewa/api/views_assets_tracks.py

from rest_framework import viewsets, filters
from tewa.models import DefendedAsset, Track
from tewa.api.serializers import DefendedAssetSerializer, TrackSerializer
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class DefendedAssetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DefendedAssetSerializer
    pagination_class = None  # DA list is usually short

    def get_queryset(self):
        qs = DefendedAsset.objects.all()
        scenario_id = self.request.query_params.get("scenario_id")
        if scenario_id:
            qs = qs.filter(scenario_id=scenario_id)
        return qs.order_by("id")

class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Track.objects.all()
        scenario_id = self.request.query_params.get("scenario_id")
        if scenario_id:
            qs = qs.filter(scenario_id=scenario_id)
        return qs.order_by("id")

