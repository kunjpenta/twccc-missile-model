# tewa/tests/test_threatscores_parity.py
from decimal import Decimal

import pytest
from django.urls import reverse

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track
from tewa.services.threat_compute import (
    batch_compute_for_scenario,  # ✅ correct import
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded_threatscores():
    """Seed deterministic scenario with known lat/lon coordinate schema."""
    s = Scenario.objects.create(name="Scenario-ParityTest")

    # Defended Asset (center)
    da = DefendedAsset.objects.create(
        scenario=s,
        name="DA-Test",
        lat=0.0,
        lon=0.0,
        radius_km=10.0,
    )

    # Track (slightly offset from DA)
    t = Track.objects.create(
        scenario=s,
        track_id="T-Alpha",
        lat=0.1,
        lon=0.1,
        alt_m=1000.0,           # ✅ Add altitude to satisfy NOT NULL
        speed_mps=250.0,
        heading_deg=225.0,
    )

    # Compute and persist threat scores
    from tewa.services.threat_compute import batch_compute_for_scenario
    batch_compute_for_scenario(s.id, da.id)

    return s


def _approx_equal(a, b, tol=1e-6):
    return abs(Decimal(a) - Decimal(b)) <= Decimal(str(tol))


def test_threatscores_api_matches_db(client, seeded_threatscores):
    """Verify API and DB ThreatScores parity within rounding tolerance."""
    s = seeded_threatscores
    url = reverse("tewa_api:api_threatscores", kwargs={"scenario_id": s.id})
    resp = client.get(url)
    assert resp.status_code == 200

    api_rows = resp.json()
    db_rows = list(ThreatScore.objects.filter(scenario=s).order_by("id"))

    assert len(api_rows) == len(db_rows) > 0

    for api_row, db_row in zip(api_rows, db_rows):
        for field in ["cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score"]:
            a = round(float(api_row[field]), 8)
            b = round(float(getattr(db_row, field)), 8)
            assert _approx_equal(a, b), f"{field} mismatch: {a} vs {b}"

    # Confirm API sorted by score descending
    api_sorted = sorted(api_rows, key=lambda x: x["score"], reverse=True)
    assert api_rows == api_sorted


def test_snapshot_guard(client, seeded_threatscores, snapshot):
    """Guard against formula drift (snapshot of deterministic outputs)."""
    s = seeded_threatscores
    url = reverse("tewa_api:api_threatscores", kwargs={"scenario_id": s.id})
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()

    for row in data:
        for key in ["cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score"]:
            row[key] = round(float(row[key]), 6)

    snapshot.assert_match(data)
