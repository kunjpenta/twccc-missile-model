# core/enums.py
from __future__ import annotations

from enum import Enum


class InterpMethod(str, Enum):
    LINEAR = "linear"
    LATEST = "latest"
