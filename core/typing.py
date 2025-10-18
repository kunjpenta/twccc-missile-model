# core/typing.py
from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class DateTimeDict(TypedDict):
    dt: datetime   # tz-aware UTC
    iso: str       # ISO-8601 string, e.g. "...Z"
