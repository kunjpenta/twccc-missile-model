# core/utils/geodesy.py
from __future__ import annotations

import math
from dataclasses import dataclass

from .units import deg2rad, rad2deg

# WGS-84
WGS84_A = 6378137.0          # semi-major axis (m)
WGS84_F = 1 / 298.257223563  # flattening (~1/298.257...)
WGS84_B = WGS84_A * (1 - WGS84_F)
WGS84_R_MEAN = 6371008.7714  # mean Earth radius (m), good for haversine


@dataclass(frozen=True)
class LatLon:
    lat: float  # degrees
    lon: float  # degrees

# ---------------- Geodesic (spherical haversine + initial bearing) ----------------


def haversine_distance_m(p1: LatLon, p2: LatLon) -> float:
    """
    Great-circle distance using haversine on a sphere with R_mean.
    Good to <~1% error for most TEWA ranges.
    """
    lat1, lon1, lat2, lon2 = map(deg2rad, (p1.lat, p1.lon, p2.lat, p2.lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * WGS84_R_MEAN * math.asin(min(1.0, math.sqrt(h)))


def initial_bearing_deg(p1: LatLon, p2: LatLon) -> float:
    """
    Forward azimuth from p1 to p2, in degrees, where 0 = North, 90 = East.
    """
    lat1, lat2 = map(deg2rad, (p1.lat, p2.lat))
    dlon = deg2rad(p2.lon - p1.lon)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * \
        math.cos(lat2) * math.cos(dlon)
    brng = math.atan2(x, y)  # radians from North clockwise
    return (rad2deg(brng) + 360.0) % 360.0


def destination_point(p: LatLon, bearing_deg: float, distance_m: float) -> LatLon:
    """
    Move distance_m along a great circle from p at bearing_deg (0=North).
    """
    δ = distance_m / WGS84_R_MEAN
    θ = deg2rad(bearing_deg)
    φ1 = deg2rad(p.lat)
    λ1 = deg2rad(p.lon)

    sinφ2 = math.sin(φ1)*math.cos(δ) + math.cos(φ1)*math.sin(δ)*math.cos(θ)
    φ2 = math.asin(sinφ2)
    y = math.sin(θ) * math.sin(δ) * math.cos(φ1)
    x = math.cos(δ) - math.sin(φ1) * sinφ2
    λ2 = λ1 + math.atan2(y, x)

    return LatLon(rad2deg(φ2), (rad2deg(λ2) + 540.0) % 360.0 - 180.0)

# ---------------- Local tangent plane (small-angle ENU) ----------------


def enu_from_latlon(p: LatLon, origin: LatLon) -> tuple[float, float]:
    """
    Convert lat/lon near origin to ENU (east, north) in meters using
    an equirectangular small-angle approximation.
    Accurate for ~<200 km from origin; fast.
    """
    lat = deg2rad(p.lat)
    lon = deg2rad(p.lon)
    lat0 = deg2rad(origin.lat)
    lon0 = deg2rad(origin.lon)
    dlat = lat - lat0
    dlon = lon - lon0
    east = WGS84_R_MEAN * dlon * math.cos((lat + lat0) * 0.5)
    north = WGS84_R_MEAN * dlat
    return east, north


def latlon_from_enu(east_m: float, north_m: float, origin: LatLon) -> LatLon:
    """
    Inverse of enu_from_latlon.
    """
    lat0 = deg2rad(origin.lat)
    lon0 = deg2rad(origin.lon)
    lat = lat0 + north_m / WGS84_R_MEAN
    lon = lon0 + east_m / (WGS84_R_MEAN * math.cos((lat + lat0) * 0.5))
    return LatLon(rad2deg(lat), rad2deg(lon))
