# core/tests/test_api_siteconfig.py

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.viewsets import ModelViewSet

from core.api.serializers import SiteConfigSerializer  # adjust import
from core.models import SiteConfig

User = get_user_model()


@pytest.mark.django_db
def test_requires_auth(client):
    url = reverse("core_api:siteconfig-list")
    r = client.get(url)
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_crud_by_key(client):
    user = User.objects.create_user(username="u", password="p")
    client.force_login(user)

    # create
    url_list = reverse("core_api:siteconfig-list")
    r = client.post(url_list, data={"key": "ui.theme", "payload": {
                    "dark": True}}, content_type="application/json")
    assert r.status_code in (200, 201)

    # retrieve by key
    url_detail = reverse("core_api:siteconfig-detail", args=["ui.theme"])
    r = client.get(url_detail)
    assert r.status_code == 200
    assert r.json()["payload"]["dark"] is True

    # update payload
    r = client.patch(url_detail, data={"payload": {
                     "dark": False}}, content_type="application/json")
    assert r.status_code in (200, 202)
    assert r.json()["payload"]["dark"] is False


class SiteConfigViewSet(ModelViewSet):
    queryset = SiteConfig.objects.all()
    serializer_class = SiteConfigSerializer

    # 👇 important: look up by "key" and allow dots in the URL
    lookup_field = "key"
    lookup_value_regex = r".+"
