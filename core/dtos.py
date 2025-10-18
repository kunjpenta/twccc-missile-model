# core/dtos.py
from __future__ import annotations

from datetime import datetime
from typing import TypedDict

try:
    # Python 3.11+
    from typing import NotRequired, Required  # type: ignore[attr-defined]
except Exception:  # Python <= 3.10
    from typing_extensions import NotRequired, Required  # type: ignore


class TrackState(TypedDict, total=False):
    """
    Lightweight kinematic state used by sampling & threat_compute.
    Required keys cover interpolation and kinematics; the rest are optional.
    """
    # required
    lat: Required[float]
    lon: Required[float]
    alt_m: Required[float]
    speed_mps: Required[float]
    heading_deg: Required[float]
    t: Required[datetime]   # tz-aware UTC

    # optional metadata
    track_id: NotRequired[int]
    track_external_id: NotRequired[str]
    scenario_id: NotRequired[int]

    # optional precomputed components
    vx_mps: NotRequired[float]
    vy_mps: NotRequired[float]


# if you maintain an __all__, include TrackState:
try:
    __all__  # type: ignore[name-defined]
except NameError:
    __all__ = []
if "TrackState" not in __all__:
    __all__.append("TrackState")
