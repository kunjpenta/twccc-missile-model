# core/api/urls.py

# core/api/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Use your existing view locations; fall back if views_read isn't present.
try:
    from .views_read import CrewDetailViewSet, SiteConfigViewSet
except ImportError:  # pragma: no cover
    from .views import CrewDetailViewSet, SiteConfigViewSet


from .views import ConfigurationView  # your slimmer service-backed view
from .views_ops import (
    CrewDetailsView,
    CrewRoleView,
    FlightInfoIView,
    FlightInfoPOView,
    FlightInfoView,
    SAGWTypesView,
    TWCCConfigurationView,  # back-compat
    UnitSagwTypeView,
)
from .views_read import CrewDetailViewSet

app_name = "core_api"


class DottedLookupRouter(DefaultRouter):
    """
    Router that allows dots in lookup values by default (e.g., 'ui.theme').
    Still respects any viewset-level `lookup_value_regex` if set.
    """

    def get_lookup_regex(self, viewset, lookup_prefix: str = "") -> str:
        lookup_field = getattr(viewset, "lookup_field", "pk")
        base_regex = getattr(viewset, "lookup_value_regex",
                             r"[^/]+")  # allow dots
        return rf"(?P<{lookup_field}>{base_regex})"


router = DottedLookupRouter()
router.register(r"crew-details", CrewDetailViewSet, basename="crew-detail")
router.register(r"site-configs", SiteConfigViewSet, basename="siteconfig")


urlpatterns = [
    path("", include(router.urls)),
    path("configuration/", ConfigurationView.as_view(), name="configuration"),
    # New canonical config route (already used elsewhere)
    path("configuration/", ConfigurationView.as_view(), name="configuration"),

    # ---- Back-compat mappings to mirror your old project ----
    path("api/config/", TWCCConfigurationView.as_view(), name="twcc_config"),
    path("api/crewdetails/", CrewDetailsView.as_view(), name="crewdetails"),
    path("api/crewrole/", CrewRoleView.as_view(), name="crewrole"),
    path("api/flightinfo/", FlightInfoView.as_view(), name="flightinfo"),
    path("api/flightinfo_po/", FlightInfoPOView.as_view(), name="flightinfo_po"),
    path("api/flightinfo_i/", FlightInfoIView.as_view(), name="flightinfo_i"),
    path("api/sagw/types/", SAGWTypesView.as_view(), name="sagw_types"),
    path("api/flightinfo/sagw/", UnitSagwTypeView.as_view(), name="unit_sagw_type"),

]
