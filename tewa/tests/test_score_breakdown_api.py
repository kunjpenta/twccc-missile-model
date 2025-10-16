# tewa/tests/test_score_breakdown_api.py

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response as DRFResponse  # <-- add
from rest_framework.test import APIClient

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track


def test_score_breakdown_api_returns_latest(db):
    sc = Scenario.objects.create(name="demo")

    da = DefendedAsset.objects.create(
        scenario=sc,
        name="DA1",
        lat=0.0,
        lon=0.0,
        radius_km=10.0,
    )

    tr = Track.objects.create(
        scenario=sc,
        track_id="ABC123",
        lat=0.0,
        lon=0.0,
        alt_m=1000.0,
        speed_mps=250.0,
        heading_deg=90.0,
    )

    older = ThreatScore.objects.create(
        scenario=sc,
        da=da,
        track=tr,
        cpa_km=1200.5,
        tcpa_s=32.4,
        tdb_km=0.72,
        twrp_s=0.38,
        score=0.60,
    )
    older.computed_at = timezone.now() - timedelta(minutes=5)
    older.save(update_fields=["computed_at"])

    newer = ThreatScore.objects.create(
        scenario=sc,
        da=da,
        track=tr,
        cpa_km=1300.0,
        tcpa_s=30.0,
        tdb_km=0.80,
        twrp_s=0.40,
        score=0.75,
    )
    newer.computed_at = timezone.now()
    newer.save(update_fields=["computed_at"])

    client = APIClient()
    # make sure this name exists in tewa/api/urls.py
    url = reverse("score_breakdown")

    from typing import Any, Dict, cast

    resp: DRFResponse = client.get(
        url, {"scenario_id": sc.pk, "da_id": da.pk, "track_id": tr.pk})  # type: ignore[assignment]
    assert resp.status_code == 200

    # Tell the type checker it's a dict, then assert at runtime
    body = cast(Dict[str, Any], resp.data)
    assert isinstance(body, dict), f"Expected dict, got {type(body)}"

    assert body["cpa_km"] == 1300.0
    assert body["tcpa_s"] == 30.0
    assert body["tdb_km"] == 0.8
    assert body["twrp_s"] == 0.4
    assert body["total_score"] == 0.75
