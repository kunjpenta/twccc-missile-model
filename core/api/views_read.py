# core/api/views_read.py
from typing import Any, Dict, List, cast

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated  # add this import
from rest_framework.response import Response

from core.models import CrewDetail, SiteConfig

from .serializers import (
    CrewDetailIngestSerializer,
    CrewDetailSerializer,
    SiteConfigSerializer,
)


class CrewDetailViewSet(viewsets.ModelViewSet):
    """
    CRUD:
      - GET /crew-details/
      - POST /crew-details/
      - PUT/PATCH/DELETE /crew-details/{id}/

    Extra:
      - POST /crew-details/replace/   -> bulk replace (accepts legacy or new keys)
      - DELETE /crew-details/clear/   -> delete all
    """
    queryset = CrewDetail.objects.all().order_by("id")
    serializer_class = CrewDetailSerializer
    permission_classes = [IsAuthenticated]  # ← require login

    @action(detail=False, methods=["post"], url_path="replace")
    def replace(self, request):
        """
        Body: list of rows; accepts either canonical keys (unit_no, flight_no, ...)
        or legacy keys (unitno, flightno, ...). All rows are validated first;
        then the table is atomically replaced.
        """
        data = request.data
        if not isinstance(data, list):
            return Response({"detail": "Expected a list"}, status=status.HTTP_400_BAD_REQUEST)

        # Use ingest serializer to support legacy field names transparently
        ser_in = CrewDetailIngestSerializer(data=data, many=True)
        ser_in.is_valid(raise_exception=True)

        # Pylance-safe handling: validated_data is Any; ensure it's a list[dict]
        raw_validated = getattr(ser_in, "validated_data", None)
        validated: List[Dict[str, Any]] = (
            cast(List[Dict[str, Any]], raw_validated) if isinstance(
                raw_validated, list) else []
        )

        rows = [CrewDetail(**item) for item in validated]

        with transaction.atomic():
            CrewDetail.objects.all().delete()
            CrewDetail.objects.bulk_create(rows)

        out = CrewDetailSerializer(
            CrewDetail.objects.all().order_by("id"), many=True).data
        return Response(out, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"], url_path="clear")
    def clear(self, request):
        CrewDetail.objects.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SiteConfig.objects.all().order_by("key")
    serializer_class = SiteConfigSerializer
    lookup_field = "key"  # so /site-configs/<key>/ works
