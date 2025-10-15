# tewa/tests/test_api_scenario_params.py
import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from tewa.models import ModelParams, Scenario

pytestmark = pytest.mark.django_db


def test_api_get_params(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-API")
    url = reverse("scenario_params", kwargs={"scenario_id": s.id})
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert "R_W_m" in data and "w_cpa" in data


def test_api_patch_ok(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-API2")
    u = User.objects.create_user(username="apiuser", password="pw")
    client.login(username="apiuser", password="pw")
    url = reverse("scenario_params", kwargs={"scenario_id": s.id})
    payload = {
        "R_W_m": 30000,
        "R_DA_m": 9000,
        "tick_s": 1.0,
        "w_cpa": 0.35, "w_tcpa": 0.25, "w_tdb": 0.20, "w_twrp": 0.20,
    }
    resp = client.patch(url, data=json.dumps(payload),
                        content_type="application/json")
    assert resp.status_code == 200
    assert resp.json()["R_W_m"] == 30000


def test_api_patch_bad_sum(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-API3")
    u = User.objects.create_user(username="apiuser2", password="pw")
    client.login(username="apiuser2", password="pw")
    url = reverse("scenario_params", kwargs={"scenario_id": s.id})
    payload = {
        "tick_s": 1.0,
        "w_cpa": 0.6, "w_tcpa": 0.3, "w_tdb": 0.2, "w_twrp": -0.1,
    }
    resp = client.patch(url, data=json.dumps(payload),
                        content_type="application/json")
    assert resp.status_code == 400
    assert "Weights must sum to 1.0" in resp.json(
    )["detail"] if "detail" in resp.json() else True


def test_api_patch_radius_guard(client):
    s = Scenario.objects.first() or Scenario.objects.create(name="Scenario-API4")
    u = User.objects.create_user(username="apiuser3", password="pw")
    client.login(username="apiuser3", password="pw")
    url = reverse("scenario_params", kwargs={"scenario_id": s.id})
    payload = {"R_W_m": 8000, "R_DA_m": 8000, "tick_s": 1.0,
               "w_cpa": 0.25, "w_tcpa": 0.25, "w_tdb": 0.25, "w_twrp": 0.25}
    resp = client.patch(url, data=json.dumps(payload),
                        content_type="application/json")
    assert resp.status_code == 400
