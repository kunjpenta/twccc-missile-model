# tewa/tests/test_export_csv.py
import re

from django.urls import reverse


def read_streaming_to_text(resp, max_chunks=50):
    chunks = []
    for i, part in enumerate(resp.streaming_content):
        chunks.append(part.decode("utf-8"))
        if i >= max_chunks:
            break
    return "".join(chunks)


def test_export_requires_scenario_id(client):
    url = reverse("export_threat_board_csv")
    resp = client.get(url)
    assert resp.status_code == 400


def test_export_threat_board_csv_ok(client, db):
    # minimal: pick an existing scenario_id from seed (often 1)
    url = reverse("export_threat_board_csv")
    resp = client.get(url, {"scenario_id": 1, "top_n": 5})
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in resp["Content-Disposition"]

    # Read first chunk(s)
    text = read_streaming_to_text(resp)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) >= 1  # at least header

    header = [h.strip() for h in lines[0].split(",")]
    # required columns present by default
    for col in ("scenario_id", "track_id", "score", "cpa_m", "tcpa_s", "tdb_s", "twrp_s"):
        assert col in header


def test_export_threat_board_csv_fields_subset(client, db):
    url = reverse("export_threat_board_csv")
    fields = "track_id,score,cpa_m"
    resp = client.get(url, {"scenario_id": 1, "fields": fields, "top_n": 3})
    assert resp.status_code == 200

    text = read_streaming_to_text(resp)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header = [h.strip() for h in lines[0].split(",")]
    assert header == ["track_id", "score", "cpa_m"]


def test_export_filename_format(client, db):
    url = reverse("export_threat_board_csv")
    resp = client.get(
        url, {"scenario_id": 1, "da_id": 2, "at": "2025-10-15T05:42:50Z"})
    cd = resp["Content-Disposition"]
    # threat_board_s1_da2_2025-10-15T05-42-50Z.csv (or similar)
    assert "attachment; filename=" in cd
    m = re.search(r'threat_board_s1_da2_2025-10-15T05-42-50Z\.csv', cd)
    assert m, f"unexpected filename: {cd}"
