
# core/services/configuration_service.py
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional

from django.db import transaction

from core.models import TWCCConfiguration


@dataclass
class _NoDefaults:
    """
    Marker so tests that expect an empty payload initially can pass.
    We keep defaults minimal here; callers may set keys as they need.
    """
    pass


class ConfigurationService:
    """
    Singleton-style service that persists a single JSON payload in the
    active TWCCConfiguration row (is_active=True). Provides:
      - get_payload(): dict copy of cached payload
      - save(): upsert payload into the active row
      - reload(): refresh cache from DB
    """
    _instance: Optional["ConfigurationService"] = None
    _lock = RLock()

    def __new__(cls) -> "ConfigurationService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    # ------- lifecycle -------
    def _init(self) -> None:
        self._cache: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """
        Refresh in-memory cache from the most recent active TWCCConfiguration.
        If none exists yet, keep an empty payload ({}), matching test expectations.
        """
        row = (
            TWCCConfiguration.objects.filter(is_active=True)
            .order_by("-updated_at")
            .only("id", "payload")
            .first()
        )
        self._cache = dict(row.payload) if row and row.payload else {}

    # ------- public API -------
    def get_payload(self) -> Dict[str, Any]:
        """Return a shallow copy so callers cannot mutate the internal cache"""
        return dict(self._cache)

    @transaction.atomic
    def save(self) -> None:
        """
        Upsert the cache into the active TWCCConfiguration row. If none exists,
        create one with is_active=True. We do not modify the other IP/port fields
        here; those can be managed elsewhere or via admin.
        """
        row = (
            TWCCConfiguration.objects.select_for_update()
            .filter(is_active=True)
            .order_by("-updated_at")
            .first()
        )
        if row is None:
            row = TWCCConfiguration.objects.create(
                is_active=True,
                payload=self._cache,
            )
        else:
            row.payload = self._cache
            row.save(update_fields=["payload", "updated_at"])

    # (optionally you can add helpers like set/get for specific keys,
    # but the tests only require get_payload/reload/save)


def get_configuration_service() -> "ConfigurationService":
    """Factory accessor used by views/tests."""
    return ConfigurationService()
