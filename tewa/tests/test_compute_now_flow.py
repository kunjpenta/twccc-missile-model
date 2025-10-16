# tewa/tests/test_compute_now_flow.py

import pytest
from django.urls import reverse

from tewa.models import ThreatScore


@pytest.mark.django_db
def test_compute_flow_ok(client, seeded_threatscores, staff_user):
    client.force_login(staff_user)
    s = seeded_threatscores
    url = reverse("tewa:compute_now_scenario", args=[s.id])

    # safely get old timestamp (if exists)
    old_ts = ThreatScore.objects.filter(scenario=s).order_by("id").first()
    old_time = old_ts.computed_at if old_ts else None

    resp = client.post(url, follow=True)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Compute" in html or "Computation" in html

    # after compute, at least one ThreatScore must exist
    new_ts = ThreatScore.objects.filter(scenario=s).order_by("id").first()
    assert new_ts is not None

    # if there was an old one, timestamp must increase
    if old_time:
        assert new_ts.computed_at > old_time
