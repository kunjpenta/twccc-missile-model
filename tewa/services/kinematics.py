# tewa/services/kinematics.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from core.utils.geodesy import LatLon, enu_from_latlon
from core.utils.units import deg2rad, m_to_km

# -------------------------
# Helpers
# -------------------------


def heading_unit_vector(heading_deg: float) -> Tuple[float, float]:
    """
    Aviation heading: 0° = North, 90° = East, increases clockwise.
    Returns unit vector (east, north).
    """
    h = deg2rad(heading_deg)
    # east = sin(heading), north = cos(heading)
    return math.sin(h), math.cos(h)


@dataclass(frozen=True)
class CPAResult:
    """Closest-Point-of-Approach and time until it occurs (seconds)."""
    cpa_km: float
    tcpa_s: float


# -------------------------
# Core kinematics (ENU)
# -------------------------

def cpa_tcpa_km_s(
    *,
    da_lat: float, da_lon: float,
    trk_lat: float, trk_lon: float,
    speed_mps: float, heading_deg: float,
) -> CPAResult:
    """
    CPA/TCPA using straight-line motion in a local ENU frame centered at the DA.
      - CPA is min_t |p0 + v t|
      - TCPA is the argmin time t* (can be negative if closest point was in the past)
    """
    # Track position relative to DA (meters)
    p0_e, p0_n = enu_from_latlon(
        LatLon(trk_lat, trk_lon), LatLon(da_lat, da_lon))

    # Velocity vector (m/s) in ENU
    u_e, u_n = heading_unit_vector(heading_deg)
    v_e, v_n = u_e * speed_mps, u_n * speed_mps

    v2 = v_e * v_e + v_n * v_n
    if v2 <= 1e-9:
        # Stationary: CPA = current range, TCPA undefined → +inf
        return CPAResult(cpa_km=m_to_km(math.hypot(p0_e, p0_n)), tcpa_s=float("inf"))

    # Time of closest approach: t* = - (p0·v) / |v|^2
    t_star = - (p0_e * v_e + p0_n * v_n) / v2

    # CPA distance at t*
    cpa_e = p0_e + v_e * t_star
    cpa_n = p0_n + v_n * t_star
    cpa_m = math.hypot(cpa_e, cpa_n)
    return CPAResult(cpa_km=m_to_km(cpa_m), tcpa_s=t_star)


def tdb_s(
    *,
    da_lat: float, da_lon: float, da_radius_km: float,
    trk_lat: float, trk_lon: float,
    speed_mps: float, heading_deg: float,
) -> Optional[float]:
    """
    Time (seconds) until the trajectory first intersects the DA boundary circle.
    Returns:
      - 0.0 if already inside the DA radius
      - None if never intersects (moving away or misses)
      - >= 0 otherwise
    Solve |p0 + v t|^2 = R^2 for t ≥ 0 (quadratic).
    """
    R = da_radius_km * 1000.0
    p0_e, p0_n = enu_from_latlon(
        LatLon(trk_lat, trk_lon), LatLon(da_lat, da_lon))
    u_e, u_n = heading_unit_vector(heading_deg)
    v_e, v_n = u_e * speed_mps, u_n * speed_mps

    # Already inside the ring?
    if (p0_e * p0_e + p0_n * p0_n) <= (R * R):
        return 0.0

    a = v_e * v_e + v_n * v_n
    if a <= 1e-9:
        return None  # no movement

    b = 2.0 * (p0_e * v_e + p0_n * v_n)
    c = (p0_e * p0_e + p0_n * p0_n) - (R * R)

    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return None

    sqrt_disc = math.sqrt(disc)
    t1 = (-b - sqrt_disc) / (2.0 * a)
    t2 = (-b + sqrt_disc) / (2.0 * a)

    # First non-negative root is the entry time
    candidates = [t for t in (t1, t2) if t >= 0.0]
    return min(candidates) if candidates else None


def twrp_s(
    *,
    da_lat: float, da_lon: float, weapon_range_km: float,
    trk_lat: float, trk_lon: float,
    speed_mps: float, heading_deg: float,
) -> Optional[float]:
    """
    Time (seconds) to reach the weapon release range ring (same math as TDB but with weapon range).
    Returns None if no intersection.
    """
    if weapon_range_km is None or weapon_range_km <= 0.0:
        return None
    return tdb_s(
        da_lat=da_lat, da_lon=da_lon, da_radius_km=weapon_range_km,
        trk_lat=trk_lat, trk_lon=trk_lon,
        speed_mps=speed_mps, heading_deg=heading_deg,
    )


# -------------------------
# (Optional) Back-compat wrappers
# -------------------------

def cpa_tcpa(
    lat_t: float, lon_t: float, spd_mps: float, hdg_deg: float, lat_da: float, lon_da: float
) -> CPAResult:
    """
    Legacy signature wrapper that returns CPAResult with (tcpa_s, cpa_km) fields.
    Uses the ENU-based cpa_tcpa_km_s under the hood.
    """
    res = cpa_tcpa_km_s(
        da_lat=lat_da, da_lon=lon_da,
        trk_lat=lat_t, trk_lon=lon_t,
        speed_mps=spd_mps, heading_deg=hdg_deg,
    )
    return res


def time_to_da_boundary_s(
    lat_t: float, lon_t: float, spd_mps: float, hdg_deg: float,
    lat_da: float, lon_da: float, da_radius_km: float
) -> Optional[float]:
    return tdb_s(
        da_lat=lat_da, da_lon=lon_da, da_radius_km=da_radius_km,
        trk_lat=lat_t, trk_lon=lon_t,
        speed_mps=spd_mps, heading_deg=hdg_deg,
    )


def time_to_weapon_release_s(
    lat_t: float, lon_t: float, spd_mps: float, hdg_deg: float,
    lat_da: float, lon_da: float, weapon_range_km: float
) -> Optional[float]:
    return twrp_s(
        da_lat=lat_da, da_lon=lon_da, weapon_range_km=weapon_range_km,
        trk_lat=lat_t, trk_lon=lon_t,
        speed_mps=spd_mps, heading_deg=hdg_deg,
    )
