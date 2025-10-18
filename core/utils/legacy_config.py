# core/utils/legacy_config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping


def parse_legacy_kv_file(path: os.PathLike[str] | str) -> dict[str, str]:
    """
    Parse 'key,value' lines into a dict[str,str].
    Ignores comments (#,//,;) and blank lines. Lower-cases keys.
    """
    p = Path(path)
    data: dict[str, str] = {}
    with p.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith(("#", ";", "//")):
                continue
            if "," not in line:
                # ignore junk lines silently; tighten if you prefer raising
                continue
            k, v = line.split(",", 1)
            data[k.strip().lower()] = v.strip()
    return data


# ---------- model ----------

@dataclass(frozen=True)
class LegacyConfig:
    # Old keys -> modern names
    ows_ip: str
    ows_track_port: int
    ows_nrt_port: int
    ows_intercom_port: int
    wa_ip: str
    wa_port: int
    if_ip: str
    if_port: int
    db_ip: str
    record_flag: bool
    record_interval: int

    @staticmethod
    def _to_bool(v: str | int | bool) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            return v != 0
        s = str(v).strip().lower()
        return s in {"1", "true", "yes", "y", "on"}

    @classmethod
    def from_map(cls, m: Mapping[str, Any]) -> "LegacyConfig":
        # accept legacy lower-case keys
        def get(k: str, default: Any = None) -> Any:
            return m.get(k, default)

        return cls(
            ows_ip=str(get("owsip", "127.0.0.1")),
            ows_track_port=int(get("owstrackport", 54674)),
            ows_nrt_port=int(get("owsnrtport", 6005)),
            ows_intercom_port=int(get("owsintercomport", 6006)),
            wa_ip=str(get("waip", "127.0.0.1")),
            wa_port=int(get("waport", 6002)),
            if_ip=str(get("ifip", "127.0.0.1")),
            if_port=int(get("ifport", 6007)),
            db_ip=str(get("dbip", "127.0.0.1")),
            record_flag=cls._to_bool(get("recordflag", 0)),
            record_interval=int(get("recordinterval", 1)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ows_ip": self.ows_ip,
            "ows_track_port": self.ows_track_port,
            "ows_nrt_port": self.ows_nrt_port,
            "ows_intercom_port": self.ows_intercom_port,
            "wa_ip": self.wa_ip,
            "wa_port": self.wa_port,
            "if_ip": self.if_ip,
            "if_port": self.if_port,
            "db_ip": self.db_ip,
            "record_flag": self.record_flag,
            "record_interval": self.record_interval,
        }


# ---------- loader with env overrides ----------

ENV_MAP = {
    "ows_ip": "TWCC_OWS_IP",
    "ows_track_port": "TWCC_OWS_TRACK_PORT",
    "ows_nrt_port": "TWCC_OWS_NRT_PORT",
    "ows_intercom_port": "TWCC_OWS_INTERCOM_PORT",
    "wa_ip": "TWCC_WA_IP",
    "wa_port": "TWCC_WA_PORT",
    "if_ip": "TWCC_IF_IP",
    "if_port": "TWCC_IF_PORT",
    "db_ip": "TWCC_DB_IP",
    "record_flag": "TWCC_RECORD_FLAG",
    "record_interval": "TWCC_RECORD_INTERVAL",
}


def _apply_env_overrides(values: MutableMapping[str, Any], env: Mapping[str, str]) -> None:
    for field, env_key in ENV_MAP.items():
        if env_key in env and env[env_key] != "":
            values[field] = env[env_key]


def load_legacy_config(path: os.PathLike[str] | str, env: Mapping[str, str] | None = None) -> LegacyConfig:
    m = parse_legacy_kv_file(path)
    cfg = LegacyConfig.from_map(m)
    # apply env overrides on top
    values = cfg.as_dict()
    _apply_env_overrides(values, os.environ if env is None else env)
    # re-coerce types after overrides
    return LegacyConfig.from_map({k: v for k, v in values.items()})
