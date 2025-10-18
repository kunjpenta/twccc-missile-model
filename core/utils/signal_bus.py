# core/utils/signal_bus.py
from __future__ import annotations

from typing import Any, Callable, Dict

_SignalHandler = Callable[[Any], None]
_signal_handlers: Dict[str, _SignalHandler] = {}


def register_signal(signal_name: str, handler: _SignalHandler) -> None:
    _signal_handlers[signal_name] = handler


def emit_signal(signal_name: str, data: Any) -> None:
    """
    Fire-and-forget signal dispatcher.
    (Fixes the “handler referenced before assignment” bug.)
    """
    handler = _signal_handlers.get(signal_name)
    if handler:
        handler(data)
