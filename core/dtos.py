from dataclasses import dataclass
from typing import Any, Dict, Optional, Union


@dataclass(slots=True)
class TrackState:
    lat: float
    lon: float
    alt_m: float
    speed_mps: float
    heading_deg: float
    t_iso: Optional[str] = None


@dataclass
class ScoreBreakdownDTO:
    scenario_id: int
    da_id: int
    # Accept either the DB pk (int) or the public track id (str) in the DTO
    track_id: Union[int, str]
    ts: Optional[str]
    cpa_km: Optional[float]
    tcpa_s: Optional[float]
    tdb_km: Optional[float]
    twrp_s: Optional[float]
    total_score: Optional[float]
    # Optional payload with per-component details if you add it later
    details: Optional[Dict[str, Any]] = None
