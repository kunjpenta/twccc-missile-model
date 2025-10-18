# tewa/tests/test_api_ok_helper.py

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_ping_ok(client):
    url = reverse("tewa_api:ping")   # adjust if your name differs
    r = client.get(url)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "endpoint" in data
