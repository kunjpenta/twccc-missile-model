# tewa/tests/test_api_crew_details.py


import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import CrewDetail

User = get_user_model()


@pytest.mark.django_db
def test_list_requires_auth(client):
    url = reverse("core_api:crew-detail-list")
    r = client.get(url)
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_crud_and_replace_clear(client):
    user = User.objects.create_user(username="u1", password="pass123")
    client.force_login(user)

    url_list = reverse("core_api:crew-detail-list")
    url_replace = reverse("core_api:crew-detail-replace")
    url_clear = reverse("core_api:crew-detail-clear")

    # create one (all required fields)
    create_payload = {
        "unit_no": "U-01",
        "flight_no": "FL-11",
        "crew_role": "Pilot",
        "crew_name": "A",
        "personal_no": "P1",
        "cat_state": "Active",
        "current_datetime": "2025-10-17T12:00:00Z",
    }
    r = client.post(url_list, data=create_payload,
                    content_type="application/json")
    assert r.status_code in (200, 201)
    crew_id = r.json()["id"]
    assert isinstance(crew_id, int)

    # replace with two rows (all required fields)
    replace_payload = [
        {
            "unit_no": "U-10",
            "flight_no": "FL-10",
            "crew_role": "WSO",
            "crew_name": "B",
            "personal_no": "P2",
            "cat_state": "Active",
            "current_datetime": "2025-10-17T12:01:00Z",
        },
        {
            "unit_no": "U-20",
            "flight_no": "FL-20",
            "crew_role": "Pilot",
            "crew_name": "C",
            "personal_no": "P3",
            "cat_state": "Reserve",
            "current_datetime": "2025-10-17T12:02:00Z",
        },
    ]
    r = client.post(url_replace, data=replace_payload,
                    content_type="application/json")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == 2
    assert CrewDetail.objects.count() == 2

    # clear
    r = client.delete(url_clear)
    assert r.status_code == 204
    assert CrewDetail.objects.count() == 0
