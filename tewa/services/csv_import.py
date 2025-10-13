# tewa/services/csv_import.py

import csv
from io import StringIO
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from tewa.models import Scenario, Track, TrackSample


def _parse_ts_aware_utc(ts_str: str):
    """
    Converts a timestamp string to a timezone-aware UTC datetime object.
    """
    from dateutil.parser import parse
    dt = parse(ts_str)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


def _strip_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strips any leading/trailing whitespaces from the values in the row.
    """
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def import_csv(file_content: str, *, scenario_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Parse CSV and create Track + TrackSample rows.
    - Accepts optional scenario_id to scope tracks; if omitted, a default Scenario is used.
    - Expects headers:
      track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp
    """
    # Ensure we have a Scenario (Track.scenario is typically NOT NULL)
    scenario: Optional[Scenario]
    if scenario_id is not None:
        try:
            scenario = Scenario.objects.get(id=scenario_id)
        except Scenario.DoesNotExist:
            return {"message": "Upload failed", "errors": [f"Scenario {scenario_id} not found"]}
    else:
        # Reuse/create a default scenario for CSV imports
        scenario, _ = Scenario.objects.get_or_create(
            name="CSV Import",
            defaults={"start_time": timezone.now()},
        )

    # Be tolerant of spaces after commas in CSV
    reader = csv.DictReader(StringIO(file_content), skipinitialspace=True)

    created_tracks = 0
    created_samples = 0
    rows_processed = 0
    errors: List[str] = []

    for row in reader:
        rows_processed += 1
        try:
            row = _strip_row(row)

            # Skip empty/blank rows (common trailing line)
            if not row.get("track_id"):
                continue

            # Required columns
            required = ["track_id", "lat", "lon", "alt_m",
                        "speed_mps", "heading_deg", "timestamp"]
            missing = [k for k in required if row.get(k) in (None, "")]
            if missing:
                errors.append(f"Row {rows_processed}: missing {missing}")
                continue

            # Parse values
            track_id = row["track_id"]
            lat = float(row["lat"])
            lon = float(row["lon"])
            alt_m = float(row["alt_m"])
            speed_mps = float(row["speed_mps"])
            heading_deg = float(row["heading_deg"])

            try:
                t = _parse_ts_aware_utc(row["timestamp"])
            except Exception as e:
                # Fall back to now() but record the issue
                errors.append(
                    f"Row {rows_processed}: bad timestamp {row['timestamp']!r} ({e}); using now()")
                t = timezone.now()

            # Create (or fetch) Track with defaults for required snapshot fields
            with transaction.atomic():
                track, created = Track.objects.get_or_create(
                    scenario=scenario,  # now guaranteed non-null
                    track_id=track_id,
                    defaults={
                        "lat": lat,
                        "lon": lon,
                        "alt_m": alt_m,
                        "speed_mps": speed_mps,
                        "heading_deg": heading_deg,
                    },
                )
                if created:
                    created_tracks += 1
                else:
                    # Update snapshot to latest row (simple policy)
                    track.lat = lat
                    track.lon = lon
                    track.alt_m = alt_m
                    track.speed_mps = speed_mps
                    track.heading_deg = heading_deg
                    # 'updated_at' exists if your models inherit TimeStamped; if not, drop it.
                    track.save(update_fields=[
                               "lat", "lon", "alt_m", "speed_mps", "heading_deg", "updated_at"])

                # Create TrackSample (dedupe on (track, t))
                try:
                    _, created_sample = TrackSample.objects.get_or_create(
                        track=track,
                        t=t,
                        defaults={
                            "lat": lat,
                            "lon": lon,
                            "alt_m": alt_m,
                            "speed_mps": speed_mps,
                            "heading_deg": heading_deg,
                        },
                    )
                    if created_sample:
                        created_samples += 1
                except ValidationError as e:
                    errors.append(f"Row {rows_processed} error: {e}")

        except Exception as e:
            errors.append(f"Row {rows_processed} error: {e}")

    return {
        "message": "Upload ok",
        "tracks_created": created_tracks,
        "samples_created": created_samples,
        "rows_processed": rows_processed,
        "errors": errors,
    }
