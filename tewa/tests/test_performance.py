# tewa/tests/test_performance.py
import time
from datetime import datetime, timedelta, timezone

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tewa.models import DefendedAsset, Scenario, ThreatScore, Track, TrackSample
from tewa.services.ranking import get_ranking_for_scenario


@pytest.mark.django_db
def test_ranking_query_performance(django_assert_num_queries):
    """Benchmark query count and timing for ranking queries."""
    # --- Setup base objects ---
    scenario = Scenario.objects.create(name="PerfTest")
    da = DefendedAsset.objects.create(
        scenario=scenario,
        name="DA-Alpha",
        lat=26.9,
        lon=75.8,
        radius_km=8.0,
    )

    track = Track.objects.create(
        scenario=scenario,
        track_id="T1",
        lat=0.0,
        lon=0.0,
        alt_m=0.0,
        speed_mps=250.0,
        heading_deg=90.0,
    )

    # --- Create TrackSamples ---
    base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    samples = [
        TrackSample(
            track=track,
            t=base_time + timedelta(seconds=i),
            lat=i * 0.001,
            lon=i * 0.001,
            alt_m=1000.0 + i,
            speed_mps=250.0 + (i * 0.1),
            heading_deg=(90.0 + i) % 360,
        )
        for i in range(1000)
    ]
    TrackSample.objects.bulk_create(samples, batch_size=500)

    # --- Create ThreatScores ---
    for i in range(1000):
        ThreatScore.objects.create(
            scenario=scenario,
            da=da,            # ✅ real FK
            track=track,
            score=i / 1000.0,
        )

    # --- Benchmark ---
    with CaptureQueriesContext(connection) as ctx:
        start = time.perf_counter()
        list(get_ranking_for_scenario(scenario.id))
        end = time.perf_counter()

    duration = end - start
    query_count = len(ctx.captured_queries)
    print(f"\n⏱ Query Time: {duration:.4f}s | Queries: {query_count}")

    assert duration < 1.0, f"Ranking query too slow (>1s): {duration:.2f}s"
    assert query_count <= 5, f"Too many queries executed: {query_count}"
