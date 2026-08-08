from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Network:
    network_id: str
    network_code: str
    network_name: str
    tenant_id: str
    ota_region: str
    status: str
