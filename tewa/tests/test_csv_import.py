# tewa/tests/test_csv_import_service.py
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from tewa.services.csv_import import import_csv


class CsvImportTest(TestCase):
    def test_csv_import(self):
        # Avoid leading spaces in CSV lines.
        csv_content = (
            "track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp\n"
            "T1,26.85,80.95,1200,250,45,2025-09-30T06:05:00Z\n"
            "T2,26.86,80.96,1200,250,46,2025-09-30T06:06:00Z\n"
        )

        # Simulate an uploaded file (not strictly needed if import_csv takes a string)
        file = SimpleUploadedFile(
            "tracks.csv", csv_content.encode("utf-8"), content_type="text/csv"
        )

        # import_csv expects a decoded string
        result = import_csv(file.read().decode("utf-8"))

        # Basic checks
        self.assertIsInstance(result, dict)
        self.assertIn("tracks_created", result)
        self.assertIn("samples_created", result)
        self.assertIn("errors", result)

        self.assertEqual(result["tracks_created"], 2)
        self.assertEqual(result["samples_created"], 2)
        self.assertEqual(len(result["errors"]), 0)
