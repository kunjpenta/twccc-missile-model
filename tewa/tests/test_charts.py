# tewa/tests/test_charts.py
from django.urls import reverse


def test_score_history_png_ok(client, db, seeded_scenario_with_scores):
    # Pick a known scenario/da/track from your seeding; adjust track_id if needed
    url = reverse("score_history_png")
    resp = client.get(url, {"scenario_id": 1, "da_id": 1,
                      "track_id": "T1", "width": 640, "height": 240, "smooth": 3})
    # If your seed uses numeric track PKs instead of "T1", try "1" or "3"
    if resp.status_code == 404:
        resp = client.get(url, {"scenario_id": 1, "da_id": 1, "track_id": 1})
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/png"
    body = b"".join(resp)  # streaming-safe
    assert len(body) > 500  # non-trivial PNG size


def test_score_history_png_missing_params(client):
    url = reverse("score_history_png")
    assert client.get(url).status_code == 400


def test_score_history_png_not_found(client, db):
    url = reverse("score_history_png")
    assert client.get(url, {"scenario_id": 999, "da_id": 1,
                      "track_id": "X"}).status_code in (400, 404)
