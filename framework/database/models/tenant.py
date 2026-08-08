from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tenant:
    tenant_id: str
    tenant_code: str
    tenant_name: str
    status: str
    created_at: str
