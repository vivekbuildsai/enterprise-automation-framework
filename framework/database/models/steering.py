from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteeringZone:
    zone_id: str
    zone_code: str
    country: str
    tenant_id: str
    network_id: str
    tr_type: str
    cos: str
    ota_region: str
    roamer_count: int
    data_usage_mb: int
    leakage_flag: int
    anti_sor_flag: int
    status: str
    modified_by: str
    modified_date: str

    @property
    def has_leakage(self) -> bool:
        return bool(self.leakage_flag)

    @property
    def is_anti_sor(self) -> bool:
        return bool(self.anti_sor_flag)
