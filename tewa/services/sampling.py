# tewa/services/sampling.py


from __future__ import annotations
from tewa.models import TrackSample

from dataclasses import dataclass
from typing import Optional, Tuple

from django.db.models import F, Q
from django.utils import timezone

from core.utils.geodesy import LatLon, enu_from_latlon, latlon_from_enu
from core.utils.units import wrap_deg_signed
from tewa.models import Track, TrackSample


@dataclass(frozen=True)
class TrackState:
    lat: float
    lon: float
    alt_m: float
    speed_mps: float
    heading_deg: float
    source: str  # "interp" | "sample" | "track"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_heading(a_deg: float, b_deg: float, t: float) -> float:
    """
    Interpolates heading along the shortest arc in degrees (aviation convention).
    Returns value in [0, 360).
    """
    # shortest signed delta in (-180,180]
    delta = wrap_deg_signed(b_deg - a_deg)
    h = a_deg + delta * t
    # wrap to [0,360)
    return (h % 360.0 + 360.0) % 360.0


def sample_track_state_at(
    track: Track,
    when,
    method: str = "latest",
) -> Optional[TrackState]:
    """
    Return the track state at timestamp 'when'.
    - latest : last sample at/before 'when'; fallback to Track snapshot if none
    - linear : linear interpolation between bracketing samples in local ENU
    Returns None if no usable data exists at all.
    """
    # Fetch bracketing samples
    s1 = (
        TrackSample.objects
        .filter(track=track, t__lte=when)
        .order_by("-t")
        .first()
    )
    s2 = (
        TrackSample.objects
        .filter(track=track, t__gte=when)
        .order_by("t")
        .first()
    )

    if method == "linear" and s1 and s2 and s1.t != s2.t:
        # Interpolate in ENU around s1 as origin
        origin = LatLon(s1.lat, s1.lon)
        e1, n1 = 0.0, 0.0
        e2, n2 = enu_from_latlon(LatLon(s2.lat, s2.lon), origin)
        # time fraction
        total = (s2.t - s1.t).total_seconds()
        frac = max(0.0, min(1.0, (when - s1.t).total_seconds() / total))
        e = _lerp(e1, e2, frac)
        n = _lerp(n1, n2, frac)
        p = latlon_from_enu(e, n, origin)

        alt = _lerp(s1.alt_m, s2.alt_m, frac)
        spd = _lerp(s1.speed_mps, s2.speed_mps, frac)
        hdg = _lerp_heading(s1.heading_deg, s2.heading_deg, frac)
        return TrackState(p.lat, p.lon, alt, spd, hdg, source="interp")

    # latest: prefer s1 (<= when)
    if s1:
        return TrackState(s1.lat, s1.lon, s1.alt_m, s1.speed_mps, s1.heading_deg, source="sample")

    # fallback to live snapshot on Track model
    if hasattr(track, "lat"):
        return TrackState(track.lat, track.lon, track.alt_m, track.speed_mps, track.heading_deg, source="track")

    return None


def get_state(track, when, method="latest"):
    qs = TrackSample.objects.filter(track=track, t__lte=when).order_by("-t")
    latest = qs.first()
    if latest:
        return {
            "lat": latest.lat, "lon": latest.lon, "alt_m": latest.alt_m,
            "speed_mps": latest.speed_mps, "heading_deg": latest.heading_deg,
            "sampled_at": latest.t
        }
    # Fallback to Track snapshot (if present)
    if getattr(track, "lat", None) is not None:
        return {
            "lat": track.lat, "lon": track.lon, "alt_m": track.alt_m,
            "speed_mps": track.speed_mps, "heading_deg": track.heading_deg,
            "sampled_at": timezone.now()
        }
    return None
