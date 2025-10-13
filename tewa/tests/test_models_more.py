# tewa/tests/test_models_more.py

import pytest

from tewa.models import DefendedAsset, ModelParams, Scenario


@pytest.mark.django_db
def test_modelparams_defaults_and_str():
    sc = Scenario.objects.create(name="S")
    mp = ModelParams.objects.create(scenario=sc)  # hits defaults
    assert mp.__str__()  # str branch
    assert mp.w_cpa > 0  # default set


@pytest.mark.django_db
def test_defended_asset_clean_and_str():
    sc = Scenario.objects.create(name="S")
    da = DefendedAsset.objects.create(
        scenario=sc, name="DA", lat=0, lon=0, radius_km=10)
    da.full_clean()  # hits validators/clean()
    assert "DA" in str(da)
