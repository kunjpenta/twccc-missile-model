# core/utils/utils.py

import csv
from io import StringIO

from tewa.models import Scenario, Track


def import_csv(csv_text, scenario_id=None):
    csv_file = StringIO(csv_text)
    reader = csv.DictReader(csv_file)
    rows_processed = 0
    errors = []

    for row in reader:
        try:
            track_id = row['track_id']
            lat = float(row['lat'])
            lon = float(row['lon'])
            alt_m = float(row['alt_m'])
            speed_mps = float(row['speed_mps'])
            heading_deg = float(row['heading_deg'])

            scenario = Scenario.objects.get(
                id=scenario_id) if scenario_id else None

            Track.objects.create(
                scenario=scenario,
                track_id=track_id,
                lat=lat,
                lon=lon,
                alt_m=alt_m,
                speed_mps=speed_mps,
                heading_deg=heading_deg
            )
            rows_processed += 1
        except Exception as e:
            errors.append(str(e))

    return {"rows_processed": rows_processed, "errors": errors}
