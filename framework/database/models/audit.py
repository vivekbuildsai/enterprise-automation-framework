from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditLogEntry:
    audit_id: str
    entity_type: str
    entity_id: str
    action: str
    performed_by: str
    performed_at: str
    details: str
