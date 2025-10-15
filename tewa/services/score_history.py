# tewa/services/score_history.py
from __future__ import annotations

from typing import List, Optional, Tuple

from django.db.models import Q
from django.utils.dateparse import parse_datetime

from tewa.models import ThreatScore


def _resolve_track_filter(scenario_id: int, track_id_param: str):
    """
    Accept either a Track PK (e.g., "3") or public track_id string (e.g., "T3").
    Returns a Q() suitable for ThreatScore filtering.
    """
    # Try int PK
    try:
        pk = int(str(track_id_param))
        return Q(track_id=pk)
    except (TypeError, ValueError):
        pass
    # Fallback: public id string within scenario
    return Q(track__scenario_id=scenario_id, track__track_id=str(track_id_param))


def get_score_series(
    scenario_id: int,
    da_id: int,
    track_id: str,
    dt_from: Optional[str],
    dt_to: Optional[str],
) -> List[Tuple]:
    """
    Returns [(computed_at, score), ...] ordered by time.
    """
    q_track = _resolve_track_filter(scenario_id, track_id)
    qs = ThreatScore.objects.filter(
        Q(scenario_id=scenario_id),
        Q(da_id=da_id),
        q_track,
    ).order_by("computed_at").values_list("computed_at", "score")

    if dt_from:
        f = parse_datetime(dt_from)
        if f:
            qs = qs.filter(computed_at__gte=f)
    if dt_to:
        t = parse_datetime(dt_to)
        if t:
            qs = qs.filter(computed_at__lte=t)

    return list(qs)
