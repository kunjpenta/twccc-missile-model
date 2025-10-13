# tewa/services/engine.py

from __future__ import annotations

from datetime import timezone as dt_timezone
from typing import Iterable, List, Optional, cast

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tewa.models import DefendedAsset, ModelParams, Scenario, ThreatScore, Track
from tewa.services.threat_compute import calculate_scores_for_when
from tewa.types import ParamsLike

from .sampling import sample_track_state_at
from .threat_compute import compute_score_for_state

# extend if you add more in sampling/compute
_VALID_METHODS = {"linear", "latest"}


def _parse_when_utc(when_iso: str):
    when = parse_datetime(when_iso)
    if when is None:
        raise ValueError(f"Invalid timestamp: {when_iso}")
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)
    else:
        when = when.astimezone(dt_timezone.utc)
    return when


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

    - If da_ids is None  -> compute for ALL DAs.
    - If da_ids is []    -> compute for NO DAs (explicit empty).
    - If da_ids is [..]  -> compute only for those DAs.

    Returns the list of ThreatScore rows produced (as returned by compute_score_for_state).
    """
    # Validate/normalize inputs
    when = _parse_when_utc(when_iso)

    if method not in _VALID_METHODS:
        raise ValueError(
            f"Unsupported method '{method}'. Allowed: {sorted(_VALID_METHODS)}")

    try:
        scenario = Scenario.objects.get(id=scenario_id)
    except Scenario.DoesNotExist as e:
        raise ValueError(f"Scenario {scenario_id} not found") from e

    # Get or create params once
    params, _ = ModelParams.objects.get_or_create(scenario=scenario)

    # Resolve DAs:
    # - None  => all DAs
    # - []    => none (short-circuit)
    # - [...] => filter by ids
    das: List[DefendedAsset]
    if da_ids is None:
        das = list(DefendedAsset.objects.all())
    else:
        ids = list(da_ids)
        if not ids:  # explicit empty -> nothing to do
            return []
        das = list(DefendedAsset.objects.filter(id__in=ids))

    if not das:
        return []  # nothing to compute

    # Fetch tracks for this scenario
    tracks_qs = (
        Track.objects
        .filter(scenario=scenario)
        .select_related("scenario")
        .only("id", "track_id", "scenario_id", "lat", "lon", "alt_m", "speed_mps", "heading_deg")
    )

    out: List[ThreatScore] = []

    # Iterate tracks; sample state once per (track, when); compute per DA
    for track in tracks_qs:
        state = sample_track_state_at(track, when, method=method)
        if not state:
            continue

        # Note: compute_score_for_state is assumed to persist each ThreatScore row
        # (as in your current codebase) and return the created instance.
        for da in das:
            ts = compute_score_for_state(
                scenario=scenario,
                da=da,
                track=track,
                # Django model → satisfy Protocol
                lat=state.lat,
                params=cast(ParamsLike, params),
                lon=state.lon,
                speed_mps=state.speed_mps,
                heading_deg=state.heading_deg,
                weapon_range_km=weapon_range_km,
            )
            if ts is not None:
                out.append(ts)

    return out


def run_scenario_engine(
    scenario: Scenario,
    when,
    das: Optional[Iterable[DefendedAsset]] = None,
    method: str = "linear",
    weapon_range_km: float = 20.0,
):
    """
    Convenience wrapper that uses the pure compute function (no persistence),
    useful for simulations/what-if runs.
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
