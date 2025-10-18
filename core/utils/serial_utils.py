# core/utils/serial_utils.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional, Tuple, Union, overload

from django.utils import timezone

from core.enums import (
    EngagementResultEnum,
    LaunchTypeEnum,
    OrderEnum,
)

__all__ = [
    "safe_decode",
    "parse_iso8601",
    "now_tz",
    "enum_name",
    "try_enum",
    "classify_code",
    "classify_engagement_code",
]


def safe_decode(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except Exception:
            return None
    return str(v)


def parse_iso8601(v: Any) -> Optional[datetime]:
    s = safe_decode(v)
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone=timezone.utc)
        return dt
    except Exception:
        return None


def now_tz() -> datetime:
    return timezone.now()


def enum_name(e: Any) -> Optional[str]:
    if e is None:
        return None
    try:
        return e.name  # type: ignore[attr-defined]
    except Exception:
        try:
            return str(e)
        except Exception:
            return None


def try_enum(value: Any, enum_cls):
    try:
        return enum_cls(value)
    except Exception:
        return None


@overload
def classify_code(code: int) -> Tuple[Optional[Literal["launch", "result", "order"]],
                                      Optional[Union[LaunchTypeEnum, EngagementResultEnum, OrderEnum]]]: ...


@overload
def classify_code(code: str) -> Tuple[Optional[Literal["launch", "result", "order"]],
                                      Optional[Union[LaunchTypeEnum, EngagementResultEnum, OrderEnum]]]: ...


@overload
def classify_code(code: None) -> Tuple[None, None]: ...


def classify_code(
    code: Optional[Union[int, str]]
) -> Tuple[Optional[Literal["launch", "result", "order"]],
           Optional[Union[LaunchTypeEnum, EngagementResultEnum, OrderEnum]]]:
    if code is None:
        return None, None
    lt = try_enum(code, LaunchTypeEnum)
    if lt is not None:
        return "launch", lt
    rs = try_enum(code, EngagementResultEnum)
    if rs is not None:
        return "result", rs
    od = try_enum(code, OrderEnum)
    if od is not None:
        return "order", od
    return None, None


# Back-compat alias
classify_engagement_code = classify_code
