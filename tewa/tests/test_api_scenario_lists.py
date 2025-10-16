import pytest
from django.urls import reverse

from tewa.models import DefendedAsset, Scenario, Track
from tewa.tests.factories import create_da, create_scenario, create_tracks


@pytest.mark.django_db
def test_da_list_matches_db(api_client):
    sc = create_scenario("Scenario-3")
    da1 = create_da(sc, name="DA-1")
    da2 = create_da(sc, name="DA-2")

    url = reverse("tewa_api:defendedasset-list") + f"?scenario_id={sc.id}"
    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    names = [d["name"] for d in data["results"]
             ] if "results" in data else [d["name"] for d in data]
    assert set(names) == {"DA-1", "DA-2"}
    assert len(names) == DefendedAsset.objects.filter(scenario=sc).count()


@pytest.mark.django_db
def test_track_list_pagination_and_order(api_client):
    sc = create_scenario("Scenario-3")
    create_tracks(sc, 15)  # beyond default page size 10

    url = reverse("tewa_api:track-list") + f"?scenario_id={sc.id}"
    resp1 = api_client.get(url)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "results" in data1
    assert len(data1["results"]) <= 10
    assert data1["count"] == Track.objects.filter(scenario=sc).count()

    # second page
    next_url = data1["next"]
    if next_url:
        resp2 = api_client.get(next_url)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data1["results"][0]["id"] != data2["results"][0]["id"]
