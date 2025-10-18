import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_backcompat_requires_auth(client):
    names = [
        "core_api:twcc_config",
        "core_api:crewdetails",
        "core_api:crewrole",
        "core_api:flightinfo",
        "core_api:flightinfo_po",
        "core_api:flightinfo_i",
        "core_api:sagw_types",
        "core_api:unit_sagw_type",
    ]
    for n in names:
        r = client.get(reverse(n))
        assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_backcompat_minimal_ok(client):
    u = User.objects.create_user(username="u", password="p")
    client.force_login(u)
    assert client.get(reverse("core_api:twcc_config")).status_code == 200
    assert client.get(reverse("core_api:crewdetails")).status_code == 200
    assert client.get(reverse("core_api:crewrole")).status_code == 200
