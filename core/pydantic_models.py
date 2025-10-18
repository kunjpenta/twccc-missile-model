# core/pydantic_models.py
from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class _CamelAliasModel(BaseModel):
    class Config:
        populate_by_name = True  # pydantic v2 name

        @staticmethod
        def alias_generator(field_name: str) -> str:
            parts = field_name.split("_")
            return parts[0] + "".join(p.capitalize() for p in parts[1:])


class WeaponEngagementGeometryManualModel(_CamelAliasModel):
    header: Dict = Field(alias="m_Header")
    unit_no: int
    track_no: str
    flight_no: str


class EngagementOrderModel(BaseModel):
    header: Dict[str, int] = Field(default_factory=dict)
    engagement_type: int = Field(alias="engagementType")
    track_no: str = Field(alias="trackNo")
    unit_no: int = Field(alias="unitNo")
    flight_no: str = Field(alias="flightNo")
    range_km: float = Field(alias="rangeKm")
    bearing_deg: float = Field(alias="bearingDeg")
    cue_angle_deg: float = Field(alias="cueAngleDeg")

    def as_camel_dict(self) -> Dict:
        return self.model_dump(by_alias=True)
