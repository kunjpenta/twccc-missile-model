# tewa/types.py
from __future__ import annotations
from typing import Mapping, Protocol, TypedDict, Union, runtime_checkable

from typing import Protocol, TypedDict


# Incoming dicts may be partial (e.g., tests pass only weights)
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

# Fully-coerced dict we guarantee to return from _coerce_params


# tewa/types.py


# What the code *reads/writes* at runtime (all optional so we can coerce with defaults)
class ModelParamsDict(TypedDict, total=False):
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


# Accept either a mapping (e.g., dict) or a Django model instance with attrs above
ParamLike = Union[Mapping[str, float | bool], ParamsLike]
