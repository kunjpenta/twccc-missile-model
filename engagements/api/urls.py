from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignTrackWidgetView,
    BMCEngagementSummaryViewSet,
    EngagementViewSet,
)

app_name = "engagements_api"

router = DefaultRouter()
router.register(r"bmc-engagements", BMCEngagementSummaryViewSet,
                basename="bmc-engagement")
router.register(r"engagements", EngagementViewSet, basename="engagement")

urlpatterns = [
    path("assign-track/", AssignTrackWidgetView.as_view(), name="assign-track"),
    path("", include(router.urls)),
]
