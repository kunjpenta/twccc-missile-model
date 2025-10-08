# tewa/tests/test_da_creation.py

from django.test import TestCase
from tewa.models import DefendedAsset


class DefendedAssetTest(TestCase):
    def test_da_creation(self):
        da = DefendedAsset.objects.create(
            name="DA-Test", lat=26.85, lon=80.95, radius_km=50
        )
        self.assertEqual(da.name, "DA-Test")
        self.assertEqual(da.radius_km, 50)
        self.assertEqual(str(da), "DA-Test at 26.85, 80.95 with radius 50 km")
