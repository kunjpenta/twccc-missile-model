from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class TrackState:
    lat: float
    lon: float
    alt_m: float
    speed_mps: float
    heading_deg: float
    t_iso: Optional[str] = None


@dataclass(slots=True)
class ScoreBreakdownDTO:
    scenario_id: int
    da_id: int
    track_id: int
    ts: Optional[str]
    cpa_km: Optional[float]
    tcpa_s: Optional[float]
    tdb_km: Optional[float]
    twrp_s: Optional[float]
    total_score: Optional[float]
    details: Optional[Dict[str, Any]] = None
