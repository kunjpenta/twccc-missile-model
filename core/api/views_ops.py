# core/api/views_ops.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.serializers import CrewDetailIngestSerializer, CrewDetailSerializer
from core.models import CrewDetail, CrewRole
from core.services.configuration_service import get_configuration_service
from core.services.database_queries import DatabaseQueries


# ---------- helpers ----------
def _parse_date(s: Optional[str]):
    if not s:
        return None
    try:
        # accepts "YYYY-MM-DD" or full ISO; we only use the date part
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


# ---------- Configuration ----------
class TWCCConfigurationView(APIView):
    """
    Back-compat JSON config view using your service-backed configuration.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        svc = get_configuration_service()
        return Response(svc.get_payload(), status=status.HTTP_200_OK)

    def put(self, request):
        svc = get_configuration_service()
        incoming: Dict[str, Any] = request.data or {}
        merged = {**svc.get_payload(), **incoming}
        svc._cache = merged
        svc.save()
        return Response(svc.get_payload(), status=status.HTTP_200_OK)


# ---------- CrewDetails (list/create + filters + legacy ingest) ----------
class CrewDetailsView(APIView):
    """
    GET filters (all optional):
      - role:        exact match on crew_role
      - unit_no:     exact match on unit_no
      - flight_no:   exact match on flight_no
      - date:        YYYY-MM-DD (filters by that calendar date)
      - date_from:   YYYY-MM-DD (inclusive)
      - date_to:     YYYY-MM-DD (inclusive)
      - ordering:    comma-separated order_by string(s), e.g. 'unit_no,-current_datetime'
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = request.query_params

        role = params.get("role")
        unit_no = params.get("unit_no")
        flight_no = params.get("flight_no")
        date_str = params.get("date")
        date_from_str = params.get("date_from")
        date_to_str = params.get("date_to")
        ordering = params.get("ordering")

        qs = CrewDetail.objects.all()

        if role:
            qs = qs.filter(crew_role=role)
        if unit_no:
            qs = qs.filter(unit_no=unit_no)
        if flight_no:
            qs = qs.filter(flight_no=flight_no)

        # single-day filter
        day = _parse_date(date_str)
        if day:
            qs = qs.filter(current_datetime__date=day)

        # range filter (inclusive)
        d_from = _parse_date(date_from_str)
        d_to = _parse_date(date_to_str)
        if d_from and d_to:
            qs = qs.filter(current_datetime__date__range=(d_from, d_to))
        elif d_from:
            qs = qs.filter(current_datetime__date__gte=d_from)
        elif d_to:
            qs = qs.filter(current_datetime__date__lte=d_to)

        if ordering:
            fields = [f.strip() for f in ordering.split(",") if f.strip()]
            if fields:
                qs = qs.order_by(*fields)
        else:
            qs = qs.order_by("unit_no", "flight_no", "id")

        serializer = CrewDetailSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Accepts either a single object or a list.
        Supports legacy keys via CrewDetailIngestSerializer.
        """
        data = request.data
        many = isinstance(data, list)
        ser = CrewDetailIngestSerializer(data=data, many=many)
        ser.is_valid(raise_exception=True)

        created: List[CrewDetail] = []
        if many and isinstance(ser.validated_data, list):
            # type: ignore[arg-type]
            created = [CrewDetail(**item) for item in ser.validated_data]
            CrewDetail.objects.bulk_create(created)
        else:
            obj = CrewDetail.objects.create(
                **ser.validated_data)  # type: ignore[arg-type]
            created = [obj]

        out = CrewDetailSerializer(created, many=(len(created) > 1)).data
        return Response(out, status=status.HTTP_201_CREATED)


# ---------- CrewRole (read/create via shim or direct model) ----------
class CrewRoleView(APIView):
    """
    Minimal list/create for role lookup.
    (List uses the shim for a flat payload; create uses the model.)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = DatabaseQueries.get_crew_role()
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        payload = request.data or {}
        obj = CrewRole.objects.create(
            role_id=payload.get("role_id"),
            role_name=payload.get("role_name", ""),
        )
        return Response(
            {"id": obj.pk, "role_id": obj.role_id, "role_name": obj.role_name}, status=201
        )


# ---------- FlightInfo (read-only via shim) ----------
class FlightInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = DatabaseQueries.get_unit_flight_info()
        return Response(data, status=status.HTTP_200_OK)


class FlightInfoPOView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = DatabaseQueries.get_unit_flight_info_po()
        return Response(data, status=status.HTTP_200_OK)


class FlightInfoIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = DatabaseQueries.get_unit_flight_info_i()
        return Response(data, status=status.HTTP_200_OK)


# ---------- SAGW ----------
class SAGWTypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(DatabaseQueries.get_type_of_sagw(), status=status.HTTP_200_OK)


class UnitSagwTypeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unit_no = request.query_params.get("unit_no")
        try:
            unit_no_int = int(unit_no) if unit_no is not None else None
        except ValueError:
            return Response({"detail": "unit_no must be int"}, status=400)
        if unit_no_int is None:
            return Response({"detail": "unit_no is required"}, status=400)
        val = DatabaseQueries.get_flight_sagw_type(unit_no_int)
        return Response({"unit_no": unit_no_int, "type_of_sagw_weapon": val}, status=200)
