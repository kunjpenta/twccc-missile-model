# tewa/tests/test_navigation.py

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_breadcrumbs_render(client, seeded_threatscores):
    s = seeded_threatscores
    url = reverse("tewa:scenario_detail", args=[s.id])
    resp = client.get(url)
    html = resp.content.decode()
    assert "Home" in html
    assert "Scenarios" in html
    assert f"Scenario-{s.id}" in html
