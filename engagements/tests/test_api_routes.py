import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_engagements_routes_require_auth(client):
    # list endpoints
    for name in ["engagements_api:bmc-engagement-list", "engagements_api:engagement-list"]:
        url = reverse(name)
        r = client.get(url)
        assert r.status_code in (401, 403)

    # assign-track
    url = reverse("engagements_api:assign-track")
    r = client.get(url)
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_engagements_routes_ok_when_authed(client):
    user = User.objects.create_user(username="u", password="p")
    client.force_login(user)

    url = reverse("engagements_api:bmc-engagement-list")
    r = client.get(url)
    assert r.status_code == 200
    assert r.json() == []

    url = reverse("engagements_api:engagement-list")
    r = client.get(url)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    url = reverse("engagements_api:assign-track")
    r = client.post(url, data={"track_id": 1}, content_type="application/json")
    assert r.status_code == 200
    assert r.json().get("ok") is True
