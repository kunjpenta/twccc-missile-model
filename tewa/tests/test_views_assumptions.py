# tewa/tests/test_views_assumptions.py
import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from tewa.models import ModelParams, Scenario

pytestmark = pytest.mark.django_db


def test_assumptions_get_renders_form(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-X")
    url = reverse("scenario_assumptions", kwargs={"scenario_id": s.id})
    # unauthenticated can view (read-only)
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Scenario Assumptions" in resp.content


def test_assumptions_post_valid_saves(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-Y")
    u = User.objects.create_user(username="ed", password="pw", is_staff=True)
    client.login(username="ed", password="pw")
    url = reverse("scenario_assumptions", kwargs={"scenario_id": s.id})
    data = dict(
        R_W_m=25000, R_DA_m=8000, tick_s=1.0,
        w_cpa=0.35, w_tcpa=0.25, w_tdb=0.20, w_twrp=0.20,
        sigma_cpa=1000, sigma_tcpa=10, sigma_tdb=10, sigma_twrp=10,
    )
    resp = client.post(url, data)
    assert resp.status_code in (302, 303)

    row = ModelParams.objects.values("R_W_m", "w_cpa").get(scenario=s)
    assert row["R_W_m"] == 25000
    assert row["w_cpa"] == pytest.approx(0.35)


def test_assumptions_post_bad_weights(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-Z")
    u = User.objects.create_user(username="ed2", password="pw", is_staff=True)
    client.login(username="ed2", password="pw")
    url = reverse("scenario_assumptions", kwargs={"scenario_id": s.id})
    data = dict(
        R_W_m=25000, R_DA_m=8000, tick_s=1.0,
        w_cpa=0.50, w_tcpa=0.25, w_tdb=0.20, w_twrp=0.20,  # 1.15
    )
    resp = client.post(url, data)
    assert resp.status_code == 200
    assert b"Weights must sum to 1.0" in resp.content
