# core/tests/test_serializers_core.py
from typing import Any, Dict, Mapping, cast

from core.api.serializers import CrewDetailIngestSerializer, CrewDetailSerializer


def test_ingest_maps_legacy_fields():
    data = {
        "unitno": "U-01",
        "flightno": "FL-01",
        "crewrole": "Pilot",
        "crewname": "Alice",
        "personalno": "P123",
        "catstate": "Active",
        "datetime": "2025-10-17T12:00:00Z",
    }
    ser = CrewDetailIngestSerializer(data=data)
    assert ser.is_valid(), ser.errors

    # Pylance-safe: validated_data is Any; ensure it's a Mapping[str, Any]
    raw = ser.validated_data
    assert isinstance(raw, Mapping)
    # make a concrete dict for subscript / membership
    v: Dict[str, Any] = dict(raw)

    assert v["unit_no"] == "U-01"
    assert v["flight_no"] == "FL-01"
    assert v["crew_role"] == "Pilot"
    assert v["crew_name"] == "Alice"
    assert v["personal_no"] == "P123"
    assert v["cat_state"] == "Active"
    # Legacy keys should have been mapped away
    assert "unitno" not in v
    assert "flightno" not in v


def test_canonical_serializer_accepts_current_fields():
    data = {
        "unit_no": "U-02",
        "flight_no": "FL-02",
        "crew_role": "WSO",
        "crew_name": "Bob",
        "personal_no": "P456",
        "cat_state": "Reserve",
        "current_datetime": "2025-10-17T12:05:00Z",
    }
    ser = CrewDetailSerializer(data=data)
    assert ser.is_valid(), ser.errors
