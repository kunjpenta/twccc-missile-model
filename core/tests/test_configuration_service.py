# core/tests/test_configuration_service.py

import pytest

from core.models import TWCCConfiguration
from core.services.configuration_service import get_configuration_service


@pytest.mark.django_db
def test_service_returns_copy_and_persists():
    svc = get_configuration_service()
    # no active row yet => empty cache
    assert svc.get_payload() == {}

    # edit in-memory
    first = svc.get_payload()
    first["site_name"] = "MissileModel"
    svc._cache = first  # simulate view's merge
    svc.save()

    # persisted
    row = TWCCConfiguration.objects.get(is_active=True)
    assert row.payload["site_name"] == "MissileModel"

    # fetch again via factory
    svc2 = get_configuration_service()
    p2 = svc2.get_payload()
    assert p2["site_name"] == "MissileModel"

    # update and save again
    p2["version"] = "v2"
    svc2._cache = p2
    svc2.save()
    row.refresh_from_db()
    assert row.payload["version"] == "v2"


# core/tests/test_configuration_service.py


@pytest.mark.django_db
def test_service_roundtrip():
    # in core/tests/test_configuration_service.py, inside test_service_roundtrip()
    svc = get_configuration_service()
    p1 = svc.get_payload()
    p1.setdefault("twcc_configuration", {})["base_name"] = "X"
    svc._cache = p1
    svc.save()
    svc.reload()
    p2 = svc.get_payload()
    assert p2["twcc_configuration"]["base_name"] == "X"
