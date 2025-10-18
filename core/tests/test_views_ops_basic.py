import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import CrewDetail, CrewRole, FlightInfo, TWCCConfiguration

User = get_user_model()


@pytest.mark.django_db
def test_requires_auth(client):
    for name in [
        "core_api:crewdetails",
        "core_api:flightinfo",
        "core_api:flightinfo_po",
        "core_api:flightinfo_i",
        "core_api:crewrole",
        "core_api:twcc_config",
        "core_api:sagw_types",
        "core_api:unit_sagw_type",
    ]:
        r = client.get(reverse(name))
        assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_basic_endpoints_ok(client):
    u = User.objects.create_user(username="u", password="p")
    client.force_login(u)

    # seed rows
    CrewRole.objects.create(role_id=1, role_name="Pilot")
    FlightInfo.objects.create(
        unitno=1, flightno="FL-01", type_of_sagw_weapon=7)
    CrewDetail.objects.create(
        unit_no="U-1", flight_no="FL-01", crew_role="Pilot", crew_name="A",
        personal_no="P1", cat_state="Active", current_datetime=timezone.now()
    )
    TWCCConfiguration.objects.create()  # defaults

    r = client.get(reverse("core_api:crewdetails"))
    assert r.status_code == 200 and isinstance(r.json(), list)

    r = client.get(reverse("core_api:flightinfo"))
    assert r.status_code == 200 and isinstance(r.json(), list)

    r = client.get(reverse("core_api:crewrole"))
    assert r.status_code == 200 and r.json()[0]["role_name"] == "Pilot"

    r = client.get(reverse("core_api:twcc_config"))
    assert r.status_code == 200 and isinstance(r.json(), dict)

    r = client.get(reverse("core_api:sagw_types"))
    assert r.status_code == 200

    r = client.get(reverse("core_api:unit_sagw_type") + "?unit_no=1")
    assert r.status_code == 200 and r.json()["unit_no"] == 1
