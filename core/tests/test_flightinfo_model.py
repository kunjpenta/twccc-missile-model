import pytest

from core.models import FlightInfo


@pytest.mark.django_db
def test_flightinfo_create_and_str():
    obj = FlightInfo.objects.create(
        unitno=1, flightno="FL-01", type_of_sagw_weapon=7)
    assert obj.pk is not None
    assert str(obj) == "1_FL-01"
