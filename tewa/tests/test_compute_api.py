# tewa/tests/test_compute_api.py

import pytest
from django.urls import reverse

from tewa.models import ThreatScore


@pytest.mark.django_db
def test_compute_smoke_happy_path(api_client, seeded_scenario):
    url = reverse("tewa_api:compute_now")
    payload = {"scenario_id": seeded_scenario.id, "idempotency_key": "abc123"}

    # 1️⃣ First compute call
    resp = api_client.post(url, payload, format="json")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "count" in data and data["count"] >= 1
    assert "top3" in data

    rows = ThreatScore.objects.filter(scenario=seeded_scenario)
    assert rows.count() >= 1

    # 2️⃣ Repeat with same key → idempotent (no recompute)
    resp2 = api_client.post(url, payload, format="json")
    assert resp2.status_code == 200
    assert resp2.json() == data  # identical cached result


@pytest.mark.django_db
def test_compute_auth_required(client, seeded_scenario):
    """Unauthenticated client → 403"""
    url = reverse("tewa_api:compute_now")
    resp = client.post(url, {"scenario_id": seeded_scenario.id}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_compute_missing_fields(api_client):
    """Missing scenario_id → 400"""
    url = reverse("tewa_api:compute_now")
    resp = api_client.post(url, {}, format="json")
    assert resp.status_code in (400, 422)
