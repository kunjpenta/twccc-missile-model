# core/tests/test_configuration_service.py

import pytest

from core.models import TWCCConfiguration


@pytest.mark.django_db
def test_twcc_configuration_defaults_and_network_fields():
    cfg = TWCCConfiguration.objects.create(
        payload={"site_name": "MissileModel"},
        version="v1",
        is_active=True,
    )
    # existing behavior
    assert cfg.is_active is True
    assert cfg.payload["site_name"] == "MissileModel"

    # new fields defaults
    assert cfg.ows_ip == "127.0.0.1"
    assert cfg.wa_ip == "127.0.0.1"
    assert cfg.if_ip == "127.0.0.1"
    assert cfg.db_ip == "127.0.0.1"

    assert cfg.ows_track_port == 54674
    assert cfg.ows_nrt_port == 6005
    assert cfg.ows_internal_comm_port == 6006
    assert cfg.wa_port == 6002
    assert cfg.if_port == 6007

    assert cfg.recording_flag is False
    assert cfg.record_interval == 1
