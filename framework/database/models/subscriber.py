from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Subscriber:
    subscriber_id: str
    msisdn: str
    imsi: str
    status: str
    cos: str
    tenant_id: str
    network_id: str
    created_at: str
    updated_at: str
