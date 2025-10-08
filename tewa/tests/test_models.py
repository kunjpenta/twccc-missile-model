from django.test import TestCase
from django.utils import timezone

from tewa.models import DefendedAsset, Scenario


class TestDefendedAssetScenarioModels(TestCase):
    def test_defended_asset_creation(self):
        da = DefendedAsset.objects.create(
            name="Test DA",
            lat=26.85,
            lon=80.95,
            radius_km=50.0
        )
        self.assertEqual(da.name, "Test DA")
        self.assertEqual(da.lat, 26.85)
        self.assertEqual(da.lon, 80.95)
        self.assertEqual(da.radius_km, 50.0)

    def test_scenario_creation(self):
        # Ensure start_time is set to a valid datetime (not None)
        scenario = Scenario.objects.create(
            name="Test Scenario",
            start_time=timezone.now(),  # Ensure start_time is a datetime
            notes="This is a test scenario"
        )
        self.assertEqual(scenario.name, "Test Scenario")

        # Ensure start_time is not None and check the date
        # Add an assert message for clarity
        self.assertIsNotNone(scenario.start_time, "Start time is None!")
        self.assertEqual(scenario.start_time.date(), timezone.now().date())
        self.assertEqual(scenario.notes, "This is a test scenario")
