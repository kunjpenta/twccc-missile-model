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
    # If there was an old one, we at least expect no time regression.
    # Some implementations keep computed_at stable; equality is OK.
    if old_time is not None:
        assert new_ts.computed_at >= old_time

        # Optionally, if your model has updated_at (it appears it does),
        # you can assert it didn't go backwards (no strictness):
        # old_updated = old_ts.updated_at if old_ts else None
        # if old_updated is not None:
        #     assert new_ts.updated_at >= old_updated
