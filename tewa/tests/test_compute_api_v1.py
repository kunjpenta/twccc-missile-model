import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from tewa.models import DefendedAsset, Scenario, Track

User = get_user_model()


@pytest.mark.django_db
def test_compute_now_v1_ok():
    user = User.objects.create_user(username="tester", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    # Correct fields for DefendedAsset
    da = DefendedAsset.objects.create(
        name="Base", lat=0.0, lon=0.0, radius_km=1.0
    )

    sc = Scenario.objects.create(name="Scenario-31")

    # ✅ Correct fields for Track (matches your model)
    Track.objects.create(
        scenario=sc,
        track_id="T1",
        lat=10.0,
        lon=20.0,
        alt_m=1000.0,
        speed_mps=250.0,
        heading_deg=45.0,
    )

    url = reverse("tewa_api:compute_now")
    response = client.post(url, {"scenario_id": sc.id}, format="json")

    assert response.status_code == 200, response.content
    data = response.json()
    assert "count" in data and data["count"] >= 1
    assert "top3" in data and isinstance(data["top3"], list)


@pytest.mark.django_db
def test_compute_now_v1_idempotent():
    user = User.objects.create_user(username="tester2", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    sc = Scenario.objects.create(name="Scenario-31b")
    url = reverse("tewa_api:compute_now")

    payload = {"scenario_id": sc.id, "idempotency_key": "abc123"}

    response1 = client.post(url, payload, format="json")
    response2 = client.post(url, payload, format="json")

    assert response1.status_code == 200
    assert response1.json() == response2.json()
