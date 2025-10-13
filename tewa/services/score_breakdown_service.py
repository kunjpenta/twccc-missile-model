# tewa/services/score_breakdown_service.py
from dataclasses import asdict
from typing import Any, Dict

from core.dtos import ScoreBreakdownDTO
from tewa.models import ThreatScore


class ScoreBreakdownService:
    """
    Returns a breakdown for one threat (Track vs DA) at latest compute time.
    Reads stored ThreatScore rows only (no on-the-fly compute here).
    """

    @staticmethod
    def by_ids(scenario_id: int, da_id: int, track_id: int) -> ScoreBreakdownDTO:
        ts_row = (
            ThreatScore.objects
            .filter(scenario_id=scenario_id, da_id=da_id, track_id=track_id)
            .order_by("-computed_at", "-id")
            .only("computed_at", "cpa_km", "tcpa_s", "tdb_km", "twrp_s", "score")
            .first()
        )

        if ts_row:
            return ScoreBreakdownDTO(
                scenario_id=scenario_id,
                da_id=da_id,
                track_id=track_id,
                ts=ts_row.computed_at.isoformat() if ts_row.computed_at else None,
                cpa_km=float(
                    ts_row.cpa_km) if ts_row.cpa_km is not None else None,
                tcpa_s=float(
                    ts_row.tcpa_s) if ts_row.tcpa_s is not None else None,
                tdb_km=float(
                    ts_row.tdb_km) if ts_row.tdb_km is not None else None,
                twrp_s=float(
                    ts_row.twrp_s) if ts_row.twrp_s is not None else None,
                total_score=float(
                    ts_row.score) if ts_row.score is not None else None,
                details=None,
            )

        # If nothing stored, tell the caller—your API can turn this into 404.
        raise ValueError(
            "No ThreatScore found for the given Scenario/DA/Track.")

    @staticmethod
    def as_dict(dto: ScoreBreakdownDTO) -> Dict[str, Any]:
        return asdict(dto)
