# core/enums.py
from __future__ import annotations

from enum import Enum


class InterpMethod(str, Enum):
    LINEAR = "linear"
    LATEST = "latest"


class EngagementActionEnum(str, Enum):
    """Operator/automation intent for a track relative to a DA."""
    HOLD = "hold"            # maintain posture / no kinetic action
    MONITOR = "monitor"      # watch; no vectoring
    TRACK = "track"          # actively track/escort
    INTERCEPT = "intercept"  # vector interceptor
    ENGAGE = "engage"        # commit weapons
    ABORT = "abort"          # cancel engagement


class OrderStatusEnum(str, Enum):
    """Lifecycle for queued/async jobs (e.g., compute tasks)."""
    PENDING = "pending"      # created, not yet queued
    QUEUED = "queued"        # accepted/queued
    RUNNING = "running"      # executing
    SUCCESS = "success"      # finished OK
    FAILURE = "failure"      # finished with errors
    CANCELED = "canceled"    # canceled before completion


__all__ = [
    "InterpMethod",
    "EngagementActionEnum",
    "OrderStatusEnum",
]
