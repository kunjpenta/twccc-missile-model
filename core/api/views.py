# core/api/views.py

from core.models import SiteConfig
from core.api.serializers import SiteConfigSerializer
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.api.serializers import (
    CrewDetailSerializer,
    SiteConfigSerializer,  # ✅ correct import
)
from core.models import CrewDetail, SiteConfig

# note: top-level 'core' app in your repo (not apps.core)
from core.services.configuration_service import (
    get_configuration_service,  # type: ignore
)


class ConfigurationView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # adjust as needed

    def get(self, request):
        svc = get_configuration_service()
        return Response(svc.get_payload())

    def put(self, request):
        svc = get_configuration_service()
        data = request.data or {}
        payload = svc.get_payload()
        payload.update(data)
        svc._cache = payload  # merged cache; service handles persistence
        svc.save()
        return Response(svc.get_payload(), status=status.HTTP_200_OK)


# core/api/views.py


class CrewDetailViewSet(ModelViewSet):
    queryset = CrewDetail.objects.all().order_by("id")
    serializer_class = CrewDetailSerializer
    permission_classes = [IsAuthenticated]  # ✅ tests expect list requires auth


# core/api/views.py


class SiteConfigViewSet(ModelViewSet):
    queryset = SiteConfig.objects.all()
    serializer_class = SiteConfigSerializer
    permission_classes = [IsAuthenticated]

    lookup_field = "key"
    lookup_value_regex = r"[^/]+"  # allow dots (anything except '/')
