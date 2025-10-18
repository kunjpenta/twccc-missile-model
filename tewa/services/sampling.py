# tewa/services/sampling.py
from __future__ import annotations

from datetime import timezone as dt_timezone
from typing import Optional

from django.utils import timezone as djtz

from core.dtos import TrackState
from core.utils.geodesy import LatLon, enu_from_latlon, latlon_from_enu
from tewa.models import Track, TrackSample


def _mk_state(
    lat: float,
    lon: float,
    alt_m: float,
    speed_mps: float,
    heading_deg: float,
    t,
) -> TrackState:
    """Create a TrackState TypedDict with required keys."""
    # ensure tz-aware (UTC) if someone passes naive dt
    if getattr(t, "tzinfo", None) is None:
        t = t.replace(tzinfo=dt_timezone.utc)
    return {
        "lat": float(lat),
        "lon": float(lon),
        "alt_m": float(alt_m),
        "speed_mps": float(speed_mps),
        "heading_deg": float(heading_deg),
        "t": t,
    }


def _lerp(a: float, b: float, f: float) -> float:
    return a + (b - a) * f


def _lerp_heading(h1: float, h2: float, f: float) -> float:
    """Shortest-arc interpolation of headings in degrees [0, 360)."""
    d = ((h2 - h1 + 540.0) % 360.0) - 180.0
    return (h1 + d * f) % 360.0


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
        return _mk_state(p.lat, p.lon, alt, spd, hdg, when)

    # latest: prefer s1 (<= when)
    if s1:
        return _mk_state(s1.lat, s1.lon, s1.alt_m, s1.speed_mps, s1.heading_deg, s1.t)

    # fallback to live snapshot on Track model
    if getattr(track, "lat", None) is not None:
        return _mk_state(track.lat, track.lon, track.alt_m, track.speed_mps, track.heading_deg, when)

    return None


def get_state(track, when, method: str = "latest"):
    """
    Lightweight state fetcher (dict) for templates/diagnostics.
    Not used by the threat kernels; kept for convenience.
    """
    latest = (
        TrackSample.objects
        .filter(track=track, t__lte=when)
        .order_by("-t")
        .first()
    )
    if latest:
        return {
            "lat": latest.lat,
            "lon": latest.lon,
            "alt_m": latest.alt_m,
            "speed_mps": latest.speed_mps,
            "heading_deg": latest.heading_deg,
            "sampled_at": latest.t,
        }

    # Fallback to Track snapshot (if present)
    if getattr(track, "lat", None) is not None:
        return {
            "lat": track.lat,
            "lon": track.lon,
            "alt_m": track.alt_m,
            "speed_mps": track.speed_mps,
            "heading_deg": track.heading_deg,
            "sampled_at": djtz.now(),
        }
    return None
