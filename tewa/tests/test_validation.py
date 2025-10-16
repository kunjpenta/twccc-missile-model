# tewa/tests/test_validation.py
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from tewa.models import Track, TrackSample


@pytest.mark.django_db
def test_invalid_defended_asset_radius_form(client, admin_user, django_user_model):
    """DA radius must be >0 and less than R_W"""
    from tewa.forms import DefendedAssetForm

    form = DefendedAssetForm(
        data={
            "name": "DA-Invalid",
            "lat": 12.34,
            "lon": 56.78,
            "radius_km": -100,  # invalid negative
        }
    )
    assert not form.is_valid()
    assert "radius_km" in form.errors


@pytest.mark.django_db
def test_invalid_track_coordinates(client):
    """Track latitude/longitude must be within valid ranges"""
    with pytest.raises(ValidationError):
        track = Track(track_id="T-Invalid", lat=123.45, lon=200.00, alt_m=100)
        track.full_clean()  # will trigger lat/lon validators


@pytest.mark.django_db
def test_invalid_modelparams_weights_sum(client, django_user_model, seeded_scenario_with_scores):
    """Sum of weights must equal 1.0 ±0.01 tolerance"""
    # Create & login user
    user = django_user_model.objects.create_user(
        username="testadmin", password="pass123")
    client.login(username="testadmin", password="pass123")

    sid = seeded_scenario_with_scores["scenario"].id
    url = reverse("tewa_api:scenario_params", args=[sid])

    payload = {
        "R_W_m": 50000,
        "R_DA_m": 40000,
        "tick_s": 1,
        "w_cpa": 0.4,
        "w_tcpa": 0.4,
        "w_tdb": 0.4,
        "w_twrp": 0.0,  # total = 1.2 > 1.0
    }

    # ✅ PATCH instead of POST
    response = client.patch(url, payload, content_type="application/json")
    assert response.status_code == 400
    assert b"Weights must sum to 1.0" in response.content


@pytest.mark.django_db
def test_scenario_param_range_limits(client, django_user_model, seeded_scenario_with_scores):
    """tick_s must be positive and R_W within logical bounds"""
    user = django_user_model.objects.create_user(
        username="testuser", password="pass123")
    client.login(username="testuser", password="pass123")

    sid = seeded_scenario_with_scores["scenario"].id
    url = reverse("tewa_api:scenario_params", args=[sid])

    payload = {
        "R_W_m": 10000,
        "R_DA_m": 20000,  # invalid
        "tick_s": -1,     # invalid
        "w_cpa": 0.25,
        "w_tcpa": 0.25,
        "w_tdb": 0.25,
        "w_twrp": 0.25,
    }

    response = client.patch(url, payload, content_type="application/json")
    assert response.status_code == 400
    assert b"tick_s" in response.content or b"R_DA_m" in response.content
