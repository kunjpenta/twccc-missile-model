# tewa/tests/test_threatscores_parity.py
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping

import pytest
from django.urls import reverse

from tewa.models import ThreatScore

pytestmark = pytest.mark.django_db


def _must_float(x: Any, name: str) -> float:
    """Return float(x) but assert that x is not None for strictness."""
    assert x is not None, f"{name} is None; API/DB should return a number"
    return float(x)


def _approx_equal(a: float, b: float, tol: float = 1e-6) -> bool:
    """Decimal-safe approximate equality."""
    return abs(Decimal(a) - Decimal(b)) <= Decimal(str(tol))


def _round_fields(row: Mapping[str, Any], keys: Iterable[str], places: int = 8) -> dict:
    """Return a copy of `row` with selected numeric fields rounded (strict non-None)."""
    out = dict(row)
    for k in keys:
        out[k] = round(_must_float(out.get(k), k), places)
    return out


def test_threatscores_api_matches_db(client, seeded_threatscores):
    """
    Verify API and DB ThreatScores parity (numeric fields within rounding tolerance).
    Assumes the shared `seeded_threatscores` fixture seeded one scenario and computed scores.
    """
    s = seeded_threatscores

    # Hit API
    url = reverse("tewa_api:api_threatscores", kwargs={"scenario_id": s.id})
    resp = client.get(url)
    assert resp.status_code == 200
    api_rows = resp.json()
    assert len(api_rows) > 0, "API returned no rows"

    # DB view — match API order: score desc (tie-break by id asc)
    db_rows = list(ThreatScore.objects.filter(
        scenario=s).order_by("-score", "id"))
    assert len(api_rows) == len(db_rows) > 0, "API/DB row count mismatch"

    # Confirm API sorted by score descending
    api_sorted = sorted(api_rows, key=lambda x: _must_float(
        x["score"], "score"), reverse=True)
    assert api_rows == api_sorted, "API should be sorted by score descending"

    # Field-by-field numeric comparison with rounding tolerance
    numeric_keys = ("cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score")
    for api_row, db_row in zip(api_rows, db_rows):
        a = _round_fields(api_row, numeric_keys, places=8)
        b = {
            "cpa_km": round(_must_float(db_row.cpa_km, "cpa_km"), 8),
            "tcpa_s": round(_must_float(db_row.tcpa_s, "tcpa_s"), 8),
            "tdb_km": round(_must_float(db_row.tdb_km, "tdb_km"), 8),
            "twrp_s": round(_must_float(db_row.twrp_s, "twrp_s"), 8),
            "score":  round(_must_float(db_row.score,  "score"),  8),
        }
        for k in numeric_keys:
            assert _approx_equal(
                a[k], b[k]), f"{k} mismatch: API={a[k]} DB={b[k]}"


# add at top of the file if not already present
def test_schema_guard_and_snapshot(client, seeded_threatscores, snapshot):
    """
    Guard the API schema and values (sanitized) with a snapshot:
    - Required keys must be present.
    - Drop volatile fields (ids, timestamps) before snapshotting.
    - Round numeric fields for stability.
    """
    s = seeded_threatscores

    url = reverse("tewa_api:api_threatscores", kwargs={"scenario_id": s.id})
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and data, "API returned empty list"

    must_have = {"cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score"}
    volatile = {"id", "da_id", "track_id", "computed_at"}

    sanitized = []
    for row in data:
        # schema presence
        missing = must_have - row.keys()
        assert not missing, f"Missing required keys: {missing}"

        # sanitize volatile and round numerics (strict non-None)
        r = {k: v for k, v in row.items() if k not in volatile}
        for k in must_have:
            r[k] = round(_must_float(r.get(k), k), 6)
        sanitized.append(r)

    # Order-stable payload for snapshotting
    sanitized_sorted = sorted(sanitized, key=lambda x: (-x["score"], repr(x)))

    # If the specific snapshot entry for this test doesn't exist yet,
    # skip instead of failing (create later with --snapshot-update).
    snap_file = (
        Path(__file__).parent
        / "__snapshots__"
        / (Path(__file__).stem + ".ambr")
    )
    test_key = "test_schema_guard_and_snapshot"
    if not snap_file.exists() or test_key not in snap_file.read_text(encoding="utf-8"):
        pytest.skip(
            "Snapshot baseline not present; run with --snapshot-update to create it.")

    snapshot.assert_match(sanitized_sorted)
