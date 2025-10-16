# tewa/tests/test_charts.py
from django.urls import reverse


def _body(resp):
    """Return response body for both regular and streaming responses."""
    content = getattr(resp, "content", None)
    if content is None and hasattr(resp, "streaming_content"):
        content = b"".join(resp.streaming_content)
    return content or b""


def test_score_history_png_ok(client, db, seeded_scenario_with_scores):
    s = seeded_scenario_with_scores
    url = reverse("score_history_png")
    resp = client.get(url, {
        "scenario_id": s["scenario"].id,
        "da_id": s["da"].id,
        # The view filters ThreatScore by FK id; pass the Track PK (as int or str)
        "track_id": s["track"].id,
        "width": 640,
        "height": 240,
        "smooth": 3,
    })
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/png"
    data = _body(resp)
    assert len(data) > 800  # non-trivial PNG size
    assert "Cache-Control" in resp
    assert "Last-Modified" in resp


def test_score_history_png_missing_params(client):
    url = reverse("score_history_png")
    # No query params → 400
    resp = client.get(url)
    assert resp.status_code == 400


def test_score_history_png_not_found_wrong_track(client, db, seeded_scenario_with_scores):
    s = seeded_scenario_with_scores
    url = reverse("score_history_png")
    # Correct scenario/DA, nonexistent track → 404 (or 400 depending on your view)
    resp = client.get(url, {
        "scenario_id": s["scenario"].id,
        "da_id": s["da"].id,
        "track_id": 999999,
    })
    assert resp.status_code in (404, 400)
