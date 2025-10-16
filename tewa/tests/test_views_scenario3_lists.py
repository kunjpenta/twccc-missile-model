import pytest
from django.urls import reverse

from tewa.tests.factories import create_da, create_scenario, create_tracks


@pytest.mark.django_db
def test_scenario3_view_shows_da_and_tracks(client):
    sc = create_scenario("Scenario-3")
    da = create_da(sc, name="DA-X")
    tracks = create_tracks(sc, 3)

    url = reverse("scenario_detail", args=[sc.id])
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()

    # DA presence
    assert "DA-X" in html
    assert str(da.radius_km) in html

    # Track rows equal to count
    for tr in tracks:
        assert tr.track_id in html

    # Totals displayed
    assert f"({len(tracks)})" in html


@pytest.mark.django_db
def test_empty_state_messages(client):
    sc = create_scenario("Scenario-empty")
    url = reverse("scenario_detail", args=[sc.id])
    resp = client.get(url)
    html = resp.content.decode()
    assert "No Defended Assets found" in html
    assert "No Tracks found" in html
