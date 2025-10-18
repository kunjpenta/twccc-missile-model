# tewa/tests/test_api_ok_helper.py

from tewa.api.view_utils import ok


def test_ok_returns_response_and_merges_extra():
    resp = ok("tewa_api:dummy", answer=42)
    assert resp.status_code == 200
    assert isinstance(resp.data, dict)
    assert resp.data["ok"] is True
    assert resp.data["endpoint"] == "tewa_api:dummy"
    assert resp.data["answer"] == 42
