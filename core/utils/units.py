# core/utils/units.py
from __future__ import annotations

import math

# ---- Scalars ----
M_PER_KM = 1000.0
KM_PER_NM = 1.852
M_PER_NM = KM_PER_NM * M_PER_KM        # 1852 m
FT_PER_M = 3.280839895013123
KTS_PER_MPS = 1.9438444924406048       # kt = m/s * 1.9438...
KMH_PER_MPS = 3.6

# ---- Angle helpers ----


def deg2rad(d: float) -> float:
    return d * math.pi / 180.0


def rad2deg(r: float) -> float:
    return r * 180.0 / math.pi


def wrap_deg(d: float) -> float:
    """Wrap to [0, 360)."""
    d = d % 360.0
    return d if d >= 0 else d + 360.0


def wrap_deg_signed(d: float) -> float:
    """Wrap to (-180, 180]."""
    d = (d + 180.0) % 360.0 - 180.0
    return d

# ---- Distance ----


def m_to_km(m: float) -> float:
    return m / M_PER_KM


def km_to_m(km: float) -> float:
    return km * M_PER_KM


def nm_to_km(nm: float) -> float:
    return nm * KM_PER_NM


def km_to_nm(km: float) -> float:
    return km / KM_PER_NM


def nm_to_m(nm: float) -> float:
    return nm * M_PER_NM


def m_to_nm(m: float) -> float:
    return m / M_PER_NM


def ft_to_m(ft: float) -> float:
    return ft / FT_PER_M


def m_to_ft(m: float) -> float:
    return m * FT_PER_M

# ---- Speed ----


def mps_to_kts(mps: float) -> float:
    return mps * KTS_PER_MPS


def kts_to_mps(kts: float) -> float:
    return kts / KTS_PER_MPS


def mps_to_kmh(mps: float) -> float:
    return mps * KMH_PER_MPS


def kmh_to_mps(kmh: float) -> float:
    return kmh / KMH_PER_MPS
