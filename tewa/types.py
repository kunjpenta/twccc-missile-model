# tewa/types.py
from __future__ import annotations

from typing import Mapping, Protocol, TypedDict, Union, runtime_checkable


class ModelParamsIn(TypedDict, total=False):
    w_cpa: float
    w_tcpa: float
    w_tdb: float
    w_twrp: float
    cpa_scale_km: float
    tcpa_scale_s: float
    tdb_scale_km: float
    twrp_scale_s: float
    clamp_0_1: bool


class ModelParamsDict(TypedDict, total=True):
    w_cpa: float
    w_tcpa: float
    w_tdb: float
    w_twrp: float
    cpa_scale_km: float
    tcpa_scale_s: float
    tdb_scale_km: float
    twrp_scale_s: float
    clamp_0_1: bool


@runtime_checkable
class ParamsLike(Protocol):
    w_cpa: float
    w_tcpa: float
    w_tdb: float
    w_twrp: float
    cpa_scale_km: float
    tcpa_scale_s: float
    tdb_scale_km: float
    twrp_scale_s: float
    clamp_0_1: bool


ParamLike = Union[Mapping[str, float | bool], ParamsLike]
