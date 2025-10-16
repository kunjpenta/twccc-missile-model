# tewa/services/engine.py
from __future__ import annotations

from datetime import timezone as dt_timezone
from typing import Iterable, List, Optional, cast

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tewa.models import (
    DefendedAsset,
    ModelParams,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)
from tewa.services.sampling import sample_track_state_at
from tewa.services.threat_compute import (
    calculate_scores_for_when,
    compute_score_for_track,
)
from tewa.types import ParamsLike

# ------------------------
# internal constants & utils
# ------------------------
_VALID_METHODS = {"linear", "latest"}


def _parse_when_utc(when_iso: str):
    """Convert ISO timestamp → timezone-aware UTC datetime."""
    when = parse_datetime(when_iso)
    if when is None:
        raise ValueError(f"Invalid timestamp: {when_iso}")
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)
    else:
        when = when.astimezone(dt_timezone.utc)
    return when


# ------------------------
# main TEWA compute path
# ------------------------
def compute_scores_at_timestamp(
    *,
    scenario_id: int,
    when_iso: str,
    da_ids: Optional[Iterable[int]] = None,
    method: str = "linear",
    weapon_range_km: Optional[float] = None,
) -> List[ThreatScore]:
    """
    Compute threat scores for all (Track, DA) pairs at a given timestamp.

    - If da_ids is None → compute for all DAs.
    - If da_ids is []   → return empty.
    - If da_ids is [..] → compute only for selected DAs.

    Returns: list[ThreatScore]
    """
    when = _parse_when_utc(when_iso)

    if method not in _VALID_METHODS:
        raise ValueError(
            f"Unsupported method '{method}'. Allowed: {sorted(_VALID_METHODS)}")

    try:
        scenario = Scenario.objects.get(id=scenario_id)
    except Scenario.DoesNotExist as e:
        raise ValueError(f"Scenario {scenario_id} not found") from e

    params, _ = ModelParams.objects.get_or_create(scenario=scenario)

    # Resolve DAs
    if da_ids is None:
        das = list(DefendedAsset.objects.all())
    else:
        ids = list(da_ids)
        if not ids:
            return []
        das = list(DefendedAsset.objects.filter(id__in=ids))

    if not das:
        return []

    tracks_qs = (
        Track.objects
        .filter(scenario=scenario)
        .only("id", "track_id", "lat", "lon", "alt_m", "speed_mps", "heading_deg")
    )

    results: List[ThreatScore] = []

    for track in tracks_qs.iterator():
        state = sample_track_state_at(track, when, method=method)
        if not state:
            continue

        for da in das:
            ts = compute_score_for_track(
                scenario=scenario,
                da=da,
                track=track,
                params=cast(ParamsLike, params),
                weapon_range_km=weapon_range_km or da.radius_km,
            )
            results.append(ts)

    return results


# ------------------------
# lightweight simulation (no DB writes)
# ------------------------
def run_scenario_engine(
    scenario: Scenario,
    when,
    das: Optional[Iterable[DefendedAsset]] = None,
    method: str = "linear",
    weapon_range_km: float = 20.0,
):
    """
    Simulation mode — computes threat scores without persisting them.
    Useful for analytics, playback, or visualization layers.
    """
    if method not in _VALID_METHODS:
        raise ValueError(
            f"Unsupported method '{method}'. Allowed: {sorted(_VALID_METHODS)}")

    if das is None:
        das = DefendedAsset.objects.all()

    return calculate_scores_for_when(
        scenario=scenario,
        when=when,
        das=list(das),
        method=method,
        weapon_range_km=weapon_range_km,
    )


# ------------------------
# heavy offline computation
# ------------------------
def compute_threats_for_scenario(scenario: Scenario):
    """
    Batch-compute threat scores using stored TrackSamples.
    This function is designed for long-running, high-fidelity TEWA analysis.
    """
    samples = (
        TrackSample.objects
        .filter(scenario=scenario)
        .select_related("scenario", "track")
    )

    for sample in samples.iterator(chunk_size=5000):
        # placeholder for heavy analytics or replay computations
        # e.g., compute_score_for_track(...) per sample
        pass
