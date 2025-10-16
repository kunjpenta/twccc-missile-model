# tewa/tests/test_views_assumptions.py
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from tewa.models import Scenario

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_assumptions_get_renders_form(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-X")
    url = reverse("scenario_assumptions", kwargs={"scenario_id": s.id})
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"R_W_m" in resp.content


def test_assumptions_post_valid_saves(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-Y")

    # ✅ Create a staff user (with hashed password)
    u = User.objects.create_user(username="ed", password="pw", is_staff=True)
    client.login(username="ed", password="pw")

    url = reverse("scenario_assumptions", kwargs={"scenario_id": s.id})
    data = dict(
        R_W_m=25000, R_DA_m=8000, tick_s=1.0,
        w_cpa=0.35, w_tcpa=0.25, w_tdb=0.20, w_twrp=0.20,
        sigma_cpa=1000, sigma_tcpa=10, sigma_tdb=10, sigma_twrp=10,
    )
    resp = client.post(url, data)
    # staff user should be redirected after save
    assert resp.status_code in (302, 303)


def test_assumptions_post_bad_weights(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-Z")

    # ✅ Create a staff user
    u = User.objects.create_user(username="ed2", password="pw", is_staff=True)
    client.login(username="ed2", password="pw")

    url = reverse("scenario_assumptions", kwargs={"scenario_id": s.id})
    data = dict(
        R_W_m=25000, R_DA_m=8000, tick_s=1.0,
        w_cpa=0.50, w_tcpa=0.25, w_tdb=0.20, w_twrp=0.20,  # invalid sum (1.15)
    )
    resp = client.post(url, data)
    # validation should keep user on form
    assert resp.status_code == 200
    assert b"must sum to 1.0" in resp.content or b"error" in resp.content.lower()
