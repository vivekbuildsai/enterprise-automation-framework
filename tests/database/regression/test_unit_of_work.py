from __future__ import annotations

from typing import Any

import pytest

from framework.database.exceptions import RepositoryError
from framework.database.models import Tenant
from framework.database.repositories import TenantRepository

pytestmark = [pytest.mark.regression, pytest.mark.database]


def test_unit_of_work_commits_writes_from_all_repositories(
    db_schema: None, unit_of_work_factory: Any
) -> None:
    with unit_of_work_factory() as uow:
        tenants = uow.repository(TenantRepository)
        tenants.create(
            Tenant(
                tenant_id="U1", tenant_code="X", tenant_name="X", status="ACTIVE", created_at="t"
            )
        )

    with unit_of_work_factory() as verify_uow:
        tenants = verify_uow.repository(TenantRepository)
        assert tenants.get_by_id("U1").tenant_code == "X"


def test_unit_of_work_rolls_back_all_writes_on_exception(
    db_schema: None, unit_of_work_factory: Any
) -> None:
    with pytest.raises(RuntimeError), unit_of_work_factory() as uow:
        tenants = uow.repository(TenantRepository)
        tenants.create(
            Tenant(
                tenant_id="U2", tenant_code="Y", tenant_name="Y", status="ACTIVE", created_at="t"
            )
        )
        raise RuntimeError("simulated failure mid-transaction")

    with unit_of_work_factory() as verify_uow:
        tenants = verify_uow.repository(TenantRepository)
        with pytest.raises(RepositoryError):
            tenants.get_by_id("U2")


def test_repository_instances_are_cached_within_one_unit_of_work(
    db_schema: None, unit_of_work_factory: Any
) -> None:
    with unit_of_work_factory() as uow:
        first = uow.repository(TenantRepository)
        second = uow.repository(TenantRepository)
        assert first is second
