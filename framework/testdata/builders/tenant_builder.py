from __future__ import annotations

from datetime import UTC, datetime

from framework.database.models import Tenant
from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.utilities.id_sequence import sequences
from framework.utilities.random_data import RandomData

_tenant_sequence = sequences.get("tenant")


class TenantBuilder(BaseBuilder[Tenant]):
    """Fluent builder for `framework.database.models.Tenant` — the same
    dataclass the database repository/validator layer already uses, so a
    tenant built here can go straight into `TenantRepository.create()` or
    an assertion's `expected=` dict with no conversion step.
    """

    def with_tenant_id(self, tenant_id: str) -> TenantBuilder:
        return self._set(tenant_id=tenant_id)

    def with_tenant_code(self, tenant_code: str) -> TenantBuilder:
        return self._set(tenant_code=tenant_code)

    def with_tenant_name(self, tenant_name: str) -> TenantBuilder:
        return self._set(tenant_name=tenant_name)

    def with_status(self, status: str) -> TenantBuilder:
        return self._set(status=status)

    def with_created_at(self, created_at: str) -> TenantBuilder:
        return self._set(created_at=created_at)

    def active(self) -> TenantBuilder:
        return self.with_status("ACTIVE")

    def suspended(self) -> TenantBuilder:
        return self.with_status("SUSPENDED")

    def build(self) -> Tenant:
        tenant_code = self._get("tenant_code", lambda: f"T{RandomData.random_int(100, 999)}")
        return Tenant(
            tenant_id=self._get("tenant_id", lambda: _tenant_sequence.next_id(prefix="TENANT")),
            tenant_code=tenant_code,
            tenant_name=self._get(
                "tenant_name", lambda: f"{RandomData.company_name()} ({tenant_code})"
            ),
            status=self._get("status", lambda: "ACTIVE"),
            created_at=self._get("created_at", lambda: datetime.now(UTC).isoformat()),
        )
