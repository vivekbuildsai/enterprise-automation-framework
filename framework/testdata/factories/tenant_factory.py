from __future__ import annotations

from typing import Any

from framework.database.models import Tenant
from framework.testdata.builders import TenantBuilder


class TenantFactory:
    @staticmethod
    def active(**overrides: Any) -> Tenant:
        return TenantBuilder().active().with_fields(**overrides).build()

    @staticmethod
    def suspended(**overrides: Any) -> Tenant:
        return TenantBuilder().suspended().with_fields(**overrides).build()
