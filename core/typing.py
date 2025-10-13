# core/typing.py

from typing import NewType, TypedDict

ScenarioId = NewType("ScenarioId", int)
TrackPK = NewType("TrackPK", int)
DefendedAssetPK = NewType("DefendedAssetPK", int)


class ScoreRow(TypedDict, total=False):
    track_id: str
    da_name: str
    score: float
    computed_at: str
