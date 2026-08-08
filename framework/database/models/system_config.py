from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemConfig:
    config_id: str
    config_key: str
    config_value: str
    category: str
    updated_by: str
    updated_at: str
