# core/services/database_queries.py
from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import connection

from core.models import CrewRole, FlightInfo, TWCCConfiguration


class DatabaseQueries:
    """
    Back-compat shim used by core/api/views_ops.py (and any 'old app' code
    you’re porting). Keep these skinny and return JSON-serializable data.
    """

    # ---- small infra helpers (optional) ----
    def __init__(self) -> None:
        self.db_host = settings.DATABASES["default"].get("HOST", "")

    def get_database_host(self) -> str:
        return self.db_host

    def reconnect_db(self) -> bool:
        try:
            connection.close()
            connection.connect()
            logging.info("Postgres Database Reconnected.")
            return True
        except Exception as e:  # pragma: no cover
            logging.error(f"Error reconnecting to database: {e}")
            return False

    # ---- TWCC config ----
    @staticmethod
    def get_twcc_config() -> Dict[str, Any]:
        """
        Return the most recent active TWCCConfiguration row as a flat dict.
        """
        row = (
            TWCCConfiguration.objects.filter(is_active=True)
            .order_by("-updated_at")
            .first()
        )
        if not row:
            return {}
        return {
            "id": row.pk,
            "version": row.version,
            "is_active": row.is_active,
            "payload": row.payload,
            "ows_ip": row.ows_ip,
            "wa_ip": row.wa_ip,
            "if_ip": row.if_ip,
            "db_ip": row.db_ip,
            "ows_track_port": row.ows_track_port,
            "ows_nrt_port": row.ows_nrt_port,
            "ows_internal_comm_port": row.ows_internal_comm_port,
            "wa_port": row.wa_port,
            "if_port": row.if_port,
            "recording_flag": row.recording_flag,
            "record_interval": row.record_interval,
            "updated_at": row.updated_at,
        }

    # Some legacy code calls a different name—keep an alias
    get_twcc_configuration = get_twcc_config

    # ---- Crew roles ----
    @staticmethod
    def get_crew_role() -> List[Dict[str, Any]]:
        """
        Return all roles as simple dicts (ordered by name).
        """
        rows = CrewRole.objects.all().order_by("role_name")
        return [{"id": r.pk, "role_id": r.role_id, "role_name": r.role_name} for r in rows]

    # ---- Flight info / SAGW lookups ----
    @staticmethod
    def get_unit_flight_info() -> List[Dict[str, Any]]:
        """
        Return all FlightInfo rows as simple dicts.
        Schema:
          [{"unitno": 1, "flightno": "FL-01", "type_of_sagw_weapon": 7}, ...]
        """
        rows = FlightInfo.objects.all().order_by("unitno", "flightno")
        return [
            {
                "unitno": r.unitno,
                "flightno": r.flightno,
                "type_of_sagw_weapon": r.type_of_sagw_weapon,
            }
            for r in rows
        ]

    @staticmethod
    def get_unit_flight_info_po() -> List[Dict[str, Any]]:
        """
        Example subset for PO (weapon types 1 or 2). Adjust if your domain differs.
        """
        rows = (
            FlightInfo.objects.filter(type_of_sagw_weapon__in=[1, 2])
            .order_by("unitno", "flightno")
        )
        return [
            {
                "unitno": r.unitno,
                "flightno": r.flightno,
                "type_of_sagw_weapon": r.type_of_sagw_weapon,
            }
            for r in rows
        ]

    @staticmethod
    def get_unit_flight_info_i() -> List[Dict[str, Any]]:
        """
        Example subset for I (weapon type 3). Adjust if your domain differs.
        """
        rows = (
            FlightInfo.objects.filter(type_of_sagw_weapon=3)
            .order_by("unitno", "flightno")
        )
        return [
            {
                "unitno": r.unitno,
                "flightno": r.flightno,
                "type_of_sagw_weapon": r.type_of_sagw_weapon,
            }
            for r in rows
        ]

    @staticmethod
    def get_type_of_sagw() -> List[Dict[str, int]]:
        """
        Distinct SAGW weapon types with counts:
        [{"type_of_sagw_weapon": 7, "count": 12}, ...]
        """
        counts = Counter(
            FlightInfo.objects.values_list("type_of_sagw_weapon", flat=True)
        )
        return [
            {"type_of_sagw_weapon": t, "count": n}
            for t, n in sorted(counts.items())
        ]

    @staticmethod
    def get_flight_sagw_type(unitno: int) -> Optional[int]:
        """
        Most common SAGW type for a given unitno (or None).
        """
        qs = FlightInfo.objects.filter(unitno=unitno).values_list(
            "type_of_sagw_weapon", flat=True
        )
        if not qs.exists():
            return None
        return Counter(qs).most_common(1)[0][0]
