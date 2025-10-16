# tewa/services/kinematics.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import (
    NamedTuple,
    Optional,  # if you keep the optional wrapper shown below
    Tuple,
)

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
) -> float:
    """
    Time (seconds) until the trajectory first intersects the DA boundary circle.
    Returns a non-negative float (seconds).

    Conventions:
      - 0.0 if already inside the DA radius
      - 0.0 if never intersects (moving away, misses, or zero speed)
      - > 0.0 otherwise (earliest non-negative root)

    Solves |p0 + v t|^2 = R^2 for t ≥ 0 (quadratic) in local ENU.
    """
    R = max(0.0, da_radius_km) * 1000.0
    p0_e, p0_n = enu_from_latlon(
        LatLon(trk_lat, trk_lon), LatLon(da_lat, da_lon))
    u_e, u_n = heading_unit_vector(heading_deg)
    v_e, v_n = u_e * speed_mps, u_n * speed_mps

    # Already inside the ring?
    if (p0_e * p0_e + p0_n * p0_n) <= (R * R):
        return 0.0

    # No meaningful movement
    a = v_e * v_e + v_n * v_n
    if a <= 1e-9:
        return 0.0

    b = 2.0 * (p0_e * v_e + p0_n * v_n)
    c = (p0_e * p0_e + p0_n * p0_n) - (R * R)

    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return 0.0

    sqrt_disc = math.sqrt(disc)
    t1 = (-b - sqrt_disc) / (2.0 * a)
    t2 = (-b + sqrt_disc) / (2.0 * a)

    # First non-negative root is the entry time
    candidates = [t for t in (t1, t2) if t >= 0.0]
    return min(candidates) if candidates else 0.0


EARTH_RADIUS_KM = 6371.0


def _deg2rad(x): return x * math.pi / 180.0


def _bearing_to_unit_vec(lat_deg, lon_deg, heading_deg):
    """Local ENU unit vector of heading at (lat, lon). Returns (ex, ey) in km basis."""
    lat = _deg2rad(lat_deg)
    # East and North basis scale (km) at latitude
    k_east = math.cos(lat) * (math.pi/180.0) * EARTH_RADIUS_KM
    k_north = (math.pi/180.0) * EARTH_RADIUS_KM
    hdg = _deg2rad(heading_deg)
    # Unit vector in EN (km-normalized axes)
    return (math.sin(hdg), math.cos(hdg), k_east, k_north)


def _da_to_track_vector_km(da_lat, da_lon, trk_lat, trk_lon):
    """Approx local EN vector from DA to track, expressed in km on EN axes."""
    latm = _deg2rad((da_lat + trk_lat)/2.0)
    k_east = math.cos(latm) * (math.pi/180.0) * EARTH_RADIUS_KM
    k_north = (math.pi/180.0) * EARTH_RADIUS_KM
    dx_km = (trk_lon - da_lon) * k_east
    dy_km = (trk_lat - da_lat) * k_north
    return dx_km, dy_km


def twrp_s(
    da_lat, da_lon, weapon_range_km,
    trk_lat, trk_lon,
    speed_mps, heading_deg
):
    # Vector DA -> Track in km
    dx_km, dy_km = _da_to_track_vector_km(da_lat, da_lon, trk_lat, trk_lon)
    d_km = math.hypot(dx_km, dy_km)

    # Already inside: time is 0 by definition (NOT the failing case)
    if d_km <= weapon_range_km:
        return 0.0

    # Track ground velocity vector (km/s) in local EN frame
    ex, ey, k_east, k_north = _bearing_to_unit_vec(
        trk_lat, trk_lon, heading_deg)
    v_e_kmps = (speed_mps / 1000.0) * ex
    v_n_kmps = (speed_mps / 1000.0) * ey

    # Unit radial vector pointing Track -> DA is - (DA->Track)/d
    if d_km == 0:
        return 0.0  # degenerate but safe

    rhat_e = -dx_km / d_km
    rhat_n = -dy_km / d_km

    # Closing speed is projection of velocity onto rhat (km/s)
    closing_kmps = v_e_kmps * rhat_e + v_n_kmps * rhat_n

    # Moving away or tangential → no penetration
    if closing_kmps <= 0:
        return None

    # Time to reach range boundary (seconds)
    dist_to_boundary_km = d_km - weapon_range_km
    return dist_to_boundary_km / closing_kmps


class KinematicsBundle(NamedTuple):
    cpa_km: float
    tcpa_s: float
    tdb_s: float
    twrp_s: Optional[float] = None

    @property
    def tdb_km(self) -> float:
        # Alias for consumers that expect "km"
        return self.tdb_s

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


def compute_cpa_tcpa_tdb_twrp(
    *,
    da_lat: float, da_lon: float, da_radius_km: float,
    trk_lat: float, trk_lon: float, speed_mps: float, heading_deg: float,
    weapon_range_km: float
) -> KinematicsBundle:
    """
    Convenience wrapper that returns all 4 components in consistent units.
      - cpa_km: km
      - tcpa_s: seconds (can be negative if closest point was in the past)
      - tdb_s: seconds (0 if already inside / no intersection / zero speed)
      - twrp_s: seconds (None if never closes to the weapon range boundary)
    """
    # CPA/TCPA
    _cpa = cpa_tcpa_km_s(
        da_lat=da_lat, da_lon=da_lon,
        trk_lat=trk_lat, trk_lon=trk_lon,
        speed_mps=speed_mps, heading_deg=heading_deg,
    )

    # Time to DA boundary (s)
    _tdb_s = tdb_s(
        da_lat=da_lat, da_lon=da_lon, da_radius_km=da_radius_km,
        trk_lat=trk_lat, trk_lon=trk_lon,
        speed_mps=speed_mps, heading_deg=heading_deg,
    )

    # Time to weapon range penetration (s or None)
    _twrp_s = twrp_s(
        da_lat=da_lat, da_lon=da_lon, weapon_range_km=weapon_range_km,
        trk_lat=trk_lat, trk_lon=trk_lon,
        speed_mps=speed_mps, heading_deg=heading_deg,
    )

    return KinematicsBundle(
        cpa_km=_cpa.cpa_km,
        tcpa_s=_cpa.tcpa_s,
        tdb_s=_tdb_s,
        twrp_s=_twrp_s
    )
