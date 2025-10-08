# tewa/types.py
from typing import Protocol


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
