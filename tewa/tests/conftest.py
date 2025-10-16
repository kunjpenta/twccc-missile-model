# tewa/tests/conftest.py
from tewa.tests.factories import create_da, create_scenario, create_tracks
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import timedelta
from typing import Any, Dict

import django.urls
import pytest
from django.urls import reverse as _reverse
from django.utils import timezone


# ---------------------------------------------------------------------
# URL reverse helper — auto-prefix namespaces for backward-compatible tests
# ---------------------------------------------------------------------
def reverse(name: str, *args, **kwargs):
    """
    Automatically add correct namespace (tewa / tewa_api)
    for all known test routes.
    """
    if ":" not in name:
        api_names = {
            "score_breakdown",
            "score_history_png",
            "scenario_params",
            "export_threat_board_csv",
        }

        ui_names = {
            "home",
            "scenario_detail",
            "scenario_assumptions",
            "score_breakdown_page",
        }

        if name in api_names:
            name = f"tewa_api:{name}"
        elif name in ui_names:
            name = f"tewa:{name}"
        else:
            # fallback: assume tewa
            name = f"tewa:{name}"

    return _reverse(name, *args, **kwargs)


# ---------------------------------------------------------------------
# Common fixture to seed Scenario + DA + Track + ThreatScore for tests
# ---------------------------------------------------------------------
@pytest.fixture
def seeded_scenario_with_scores(db):
    from tewa.models import DefendedAsset, Scenario, ThreatScore, Track

    scenario = Scenario.objects.create(name="Demo-Scenario")

    def first_present(field_names: set[str], *candidates: str) -> str | None:
        for c in candidates:
            if c in field_names:
                return c
        return None

    # ---- DefendedAsset
    da_fields = {f.name for f in DefendedAsset._meta.get_fields()}
    da_kwargs: Dict[str, Any] = {"name": "DA-Alpha", "scenario": scenario}

    latf = first_present(da_fields, "lat", "latitude", "lat_deg", "y")
    if latf:
        da_kwargs[latf] = 26.90

    lonf = first_present(da_fields, "lon", "longitude", "lon_deg", "x")
    if lonf:
        da_kwargs[lonf] = 75.80

    radf = first_present(da_fields, "radius_km", "radius_m",
                         "da_radius", "r_m", "radius")
    if radf:
        da_kwargs[radf] = 8.0 if radf.endswith("km") else 8000

    da = DefendedAsset.objects.create(**da_kwargs)

    # ---- Track
    tr_fields = {f.name for f in Track._meta.get_fields()}
    tr_kwargs: Dict[str, Any] = {"scenario": scenario}

    idf = first_present(tr_fields, "track_id", "name", "callsign", "id_str")
    if idf:
        tr_kwargs[idf] = "TGT001"

    tlat = first_present(tr_fields, "lat", "latitude", "lat_deg", "y")
    if tlat:
        tr_kwargs[tlat] = 26.9058

    tlon = first_present(tr_fields, "lon", "longitude", "lon_deg", "x")
    if tlon:
        tr_kwargs[tlon] = 75.8085

    if "alt_m" in tr_fields:
        tr_kwargs["alt_m"] = 3200
    if "speed_mps" in tr_fields:
        tr_kwargs["speed_mps"] = 210

    thdg = first_present(tr_fields, "heading_deg",
                         "heading", "course_deg", "bearing_deg")
    if thdg:
        tr_kwargs[thdg] = 45

    track = Track.objects.create(**tr_kwargs)

    # ---- ThreatScore series
    now = timezone.now().replace(microsecond=0)
    for i, s in enumerate([0.20, 0.32, 0.41, 0.55, 0.62, 0.70]):
        ThreatScore.objects.create(
            scenario=scenario,
            da=da,
            track=track,
            computed_at=now + timedelta(minutes=i),
            score=s,
        )

    return {"scenario": scenario, "da": da, "track": track}


# ---------------------------------------------------------------------
# Force all reverse() imports in tests to use our patched version
# ---------------------------------------------------------------------

django.urls.reverse = reverse
print("\n[pytest setup] ✅ Patched django.urls.reverse for tests.")


User = get_user_model()


@pytest.fixture
def api_client():
    user = User.objects.create_user(username="tester_api", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def seeded_scenario(db):
    """Seed Scenario-3 with 1 DA and 3 tracks."""
    sc = create_scenario("Scenario-3")
    create_da(sc)
    create_tracks(sc, 3)
    return sc
