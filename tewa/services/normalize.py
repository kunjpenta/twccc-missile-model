# tewa/services/normalize.py

from __future__ import annotations

import math


def inv1(x: float | None, scale: float) -> float:
    """
    Monotonic decreasing map (smaller x -> larger value in (0,1]):
        f(x) = 1 / (1 + x/scale)
    Treat None or +inf as 0 (no urgency). Negative x -> 0 (invalid).
    """
    if x is None or math.isinf(x) or x < 0:
        return 0.0
    s = max(scale, 1e-9)
    return 1.0 / (1.0 + (x / s))


def clamp01(v: float | None) -> float:
    if v is None or math.isnan(v):
        return 0.0
    return max(0.0, min(1.0, v))
