# tewa/services/engine.py

from __future__ import annotations

from datetime import timezone as dt_timezone
from typing import Any, Iterable, List, Optional, cast

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tewa.models import DefendedAsset, ModelParams, Scenario, ThreatScore, Track
from tewa.services.threat_compute import calculate_scores_for_when

from .sampling import sample_track_state_at
from .threat_compute import compute_score_for_state


def compute_scores_at_timestamp(
    *,
    scenario_id: int,
    when_iso: str,
    da_ids: Optional[Iterable[int]] = None,
    method: str = "linear",
    weapon_range_km: Optional[float] = None,
) -> List[ThreatScore]:
    when = parse_datetime(when_iso)
    if when is None:
        raise ValueError(f"Invalid timestamp: {when_iso}")
    if timezone.is_naive(when):
        when = timezone.make_aware(when, dt_timezone.utc)

    scenario = Scenario.objects.get(id=scenario_id)
    params, _ = ModelParams.objects.get_or_create(scenario=scenario)

    das = list(DefendedAsset.objects.filter(id__in=list(da_ids))
               ) if da_ids else list(DefendedAsset.objects.all())

    out: List[ThreatScore] = []
    qs = Track.objects.filter(scenario=scenario).select_related("scenario")
    for track in qs:
        state = sample_track_state_at(track, when, method=method)
        if not state:
            continue
        for da in das:
            out.append(
                compute_score_for_state(
                    scenario=scenario,
                    da=da,
                    track=track,
                    # silence Pylance; runtime is fine
                    params=cast(Any, params),
                    lat=state.lat,
                    lon=state.lon,
                    speed_mps=state.speed_mps,
                    heading_deg=state.heading_deg,
                    weapon_range_km=weapon_range_km,
                )
            )
    return out


def run_scenario_engine(scenario, when, das=None, method="linear", weapon_range_km=20.0):
    if das is None:
        das = DefendedAsset.objects.all()
    return calculate_scores_for_when(
        scenario=scenario,
        when=when,
        das=das,
        method=method,
        weapon_range_km=weapon_range_km
    )
