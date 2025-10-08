from django.test import TestCase
from io import StringIO
from django.core.files.uploadedfile import SimpleUploadedFile
from tewa.services.csv_import import import_csv


class CsvImportTest(TestCase):
    def test_csv_import(self):
        csv_content = """track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp
        T1,26.85,80.95,1200,250,45,2025-09-30T06:05:00Z
        T2,26.86,80.96,1200,250,46,2025-09-30T06:06:00Z
        """

        # Simulate file upload
        file = SimpleUploadedFile(
            "tracks.csv", csv_content.encode(), content_type="text/csv")

        # Process the file content
        result = import_csv(file.read().decode('utf-8'))

        self.assertEqual(result['tracks_created'], 2)
        self.assertEqual(result['samples_created'], 2)
        self.assertEqual(len(result['errors']), 0)  # No errors
