# core/tests/test_models_crew.py

import pytest
from django.utils import timezone

from core.models import CrewDetail, CrewDetailsLegacy, CrewRole


@pytest.mark.django_db
def test_crew_detail_create_and_str():
    obj = CrewDetail.objects.create(
        unit_no="U-01",
        flight_no="FL-11",
        crew_role="Pilot",
        crew_name="Alice",
        personal_no="P123",
        cat_state="Active",
        current_datetime=timezone.now(),
    )
    assert obj.id is not None
    s = str(obj)
    assert "Alice" in s and "Pilot" in s and "U-01/FL-11" in s


@pytest.mark.django_db
def test_crew_role_unique_fields():
    r1 = CrewRole.objects.create(role_id=1, role_name="Pilot")
    assert str(r1) == "Pilot"
    with pytest.raises(Exception):
        CrewRole.objects.create(role_id=1, role_name="Pilot")  # uniq clash


@pytest.mark.django_db
def test_legacy_row_create_table_exists():
    # Optional—only if you actually use the legacy table for staging
    row = CrewDetailsLegacy.objects.create(
        unitno=10,
        flightno="FL-10",
        crewrole="WSO",
        crewname="Bob",
        personalno="P999",
        catstate="Reserve",
        datetime=timezone.now(),
    )
    assert row.id is not None
    assert str(row).startswith("Bob - FL-10")
